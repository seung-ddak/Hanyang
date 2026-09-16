from pathlib import Path
import runpy,sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'desktop'))
runpy.run_module('study_server',run_name='__main__')
