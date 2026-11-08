"""HTTP/pipeline regression tests. External LLM/dependency adapters are test doubles.
Uses the real handler, SQLite audit engine, symbolic validator and reinserter.
Does not exercise a real model or the LangGraph scheduler.
"""
import sys, pathlib, tempfile, types, unittest, threading, http.client, json
from unittest.mock import patch
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Isolate optional dependency adapters and persistent audit storage.
dotenv = types.ModuleType('dotenv'); dotenv.load_dotenv = lambda *args, **kwargs: None
sys.modules['dotenv'] = dotenv
import config
TEMP = tempfile.TemporaryDirectory(dir=ROOT / 'tests', ignore_cleanup_errors=True)
config.AUDIT_DB_PATH = pathlib.Path(TEMP.name) / 'audit.db'
class Graph:
    def __init__(self, *args): self.conditions = []
    def add_node(self, *args): pass
    def add_edge(self, *args): pass
    def set_entry_point(self, *args): pass
    def add_conditional_edges(self, *args): self.conditions.append(args)
    def compile(self): return self
langgraph = types.ModuleType('langgraph.graph'); langgraph.StateGraph = Graph; langgraph.END = 'END'
sys.modules['langgraph'] = types.ModuleType('langgraph'); sys.modules['langgraph.graph'] = langgraph
httpx = types.ModuleType('httpx'); httpx.get = lambda *a, **k: types.SimpleNamespace(status_code=200, json=lambda:{'models':[{'name':config.LOCAL_MODEL_NAME}]})
sys.modules['httpx'] = httpx
messages = types.ModuleType('langchain_core.messages')
messages.HumanMessage = messages.SystemMessage = lambda **kwargs: kwargs
sys.modules['langchain_core'] = types.ModuleType('langchain_core'); sys.modules['langchain_core.messages'] = messages
import server
from audit import audit_log
from agents import symbolic_validator, reinserter, peer_review_swarm
from pipeline.graph import build_graph

class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = server.ResilientThreadingHTTPServer(('127.0.0.1', 0), server.PrivacySwarmHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
    @classmethod
    def tearDownClass(cls): cls.server.shutdown(); cls.server.server_close(); TEMP.cleanup()
    def request(self, method, path, body=None, headers=None):
        c=http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
        if body is not None and not isinstance(body,(str,bytes)): body=json.dumps(body)
        c.request(method,path,body=body,headers=headers or {})
        r=c.getresponse(); data=r.read(); result=(r.status,dict(r.headers),data); c.close(); return result
    def test_health_configured_model(self):
        status,_,data=self.request('GET','/api/health'); self.assertEqual(status,200); self.assertTrue(json.loads(data)['ollama_online'])
    def test_health_missing_model(self):
        with patch.object(httpx,'get',return_value=types.SimpleNamespace(status_code=200,json=lambda:{'models':[]})):
            self.assertFalse(json.loads(self.request('GET','/api/health')[2])['ollama_online'])
    def test_invalid_audit_limits(self):
        for value in ['oops','-1','0','101']:
            with self.subTest(value=value): self.assertEqual(self.request('GET','/api/audit?limit='+value)[0],400)
    def test_empty_audit(self):
        status,_,data=self.request('GET','/api/audit?limit=100'); self.assertEqual(status,200); self.assertIsInstance(json.loads(data)['runs'],list)
    def test_bad_json(self): self.assertEqual(self.request('POST','/api/run','{')[0],400)
    def test_invalid_utf8(self): self.assertEqual(self.request('POST','/api/run',b'\xff')[0],400)
    def test_payload_shapes(self):
        for payload in [[],None,{'text':12},{'text':'x','task':[]},{'text':' '},{'text':'x','task':' '}]:
            with self.subTest(payload=payload): self.assertEqual(self.request('POST','/api/run',json.dumps(payload))[0],400)
    def test_document_and_instruction_limits(self):
        for payload in [{'text':'a'*30001},{'text':'x','task':'a'*2001}]: self.assertEqual(self.request('POST','/api/run',payload)[0],413)
    def test_body_size(self): self.assertEqual(self.request('POST','/api/run','a'*256001)[0],413)
    def test_external_origin_cannot_run(self):
        with patch.object(server,'run_pipeline') as run:
            self.assertEqual(self.request('POST','/api/run',{'text':'x'}, {'Origin':'https://untrusted.example'})[0],403); run.assert_not_called()
    def test_cors_not_wildcard(self):
        self.assertNotIn('Access-Control-Allow-Origin',self.request('GET','/api/audit',headers={'Origin':'https://untrusted.example'})[1])
        self.assertEqual(self.request('GET','/api/audit',headers={'Origin':'http://127.0.0.1:5173'})[1]['Access-Control-Allow-Origin'],'http://127.0.0.1:5173')
    def test_path_traversal(self):
        for path in ['/../../config.py','/%2e%2e/%2e%2e/config.py','/..%5c..%5cconfig.py']:
            with self.subTest(path=path): self.assertEqual(self.request('GET',path)[0],403)
    def test_missing_asset(self): self.assertEqual(self.request('GET','/missing.js')[0],404)
    def test_frontend(self): self.assertIn(b'PrivacySwarm', self.request('GET','/')[2])
    def test_success_response(self):
        with patch.object(server,'run_pipeline',return_value={'final_answer':'A real fixture answer','validation_passed':True}):
            status,_,data=self.request('POST','/api/run',{'text':'Test fixture'});self.assertEqual(status,200);self.assertTrue(json.loads(data)['success'])
    def test_empty_answer_is_failure(self):
        with patch.object(server,'run_pipeline',return_value={'final_answer':'','validation_passed':True}):
            self.assertFalse(json.loads(self.request('POST','/api/run',{'text':'Test fixture'})[2])['success'])
    def test_processing_exception_is_actionable(self):
        with patch.object(server,'run_pipeline',side_effect=RuntimeError('private-internal-details')):
            status,_,data=self.request('POST','/api/run',{'text':'Test fixture'});self.assertEqual(status,500);self.assertNotIn(b'private-internal-details',data)
    def test_failed_validation_blocks_routing(self):
        self.assertEqual(symbolic_validator.validator_route({'validation_passed':False,'validation_attempts':config.MAX_VALIDATION_ATTEMPTS}),'blocked')
        edges=build_graph().conditions
        self.assertEqual(next(e[2]['blocked'] for e in edges if e[0]=='symbolic_validator'),'audit_logger')
    def test_cloud_guard(self):
        result=reinserter.cloud_processor_node({'validation_passed':False});self.assertEqual(result['response_source'],'blocked');self.assertEqual(result['raw_response'],'')
    def test_missing_cloud_key_is_not_answer(self):
        with patch.object(reinserter,'GROQ_API_KEY',''):
            self.assertEqual(reinserter.cloud_processor_node({'validation_passed':True})['raw_response'],'')
    def test_instruction_identifiers_not_sent_to_cloud(self):
        result=reinserter.cloud_processor_node({'validation_passed':True,'task_description':'Send the summary to sample@example.com'})
        self.assertEqual(result['response_source'],'blocked')
        self.assertEqual(result['raw_response'],'')
    def test_missing_local_model_is_not_answer(self):
        with patch.object(peer_review_swarm,'_call_llm',return_value=''):
            self.assertEqual(peer_review_swarm.run({'sanitized_text':'sample'})['raw_response'],'')
    def test_reinsertion(self):
        self.assertEqual(reinserter.run({'raw_response':'[PERSON_1] met [PERSON_10]','reverse_map':{'[PERSON_1]':'Alpha','[PERSON_10]':'Beta'}})['final_answer'],'Alpha met Beta')
    def test_audit_failed_run(self):
        audit_log.log_run({'final_answer':'','pii_counts':{},'errors':['test fixture']})
        self.assertEqual(audit_log.get_recent_runs(1)[0]['success'],0)

if __name__=='__main__': unittest.main(verbosity=2)
