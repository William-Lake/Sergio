from argparse import ArgumentParser
from multiprocessing import Pool, freeze_support
from pathlib import Path
import json
import os
import uuid
import subprocess
import tempfile
import time
import traceback

from tqdm import tqdm


def yield_results(prog_args,term):
    
    try:
        
        command = [
            'git',
            'log',
            '--oneline','-i','-G',term]
        
        completed_process = subprocess.run(command,capture_output=True,text=True,cwd=prog_args.repo_loc.absolute().__str__())
        
        completed_process.check_returncode()
        
        for result in completed_process.stdout.splitlines():
            
            yield result
        
    except Exception as e:
        
        print(f'Exception while collecting git commit hashes!')
        
        print(str(e))
        

def gather_args(debug=False):

    arg_parser = ArgumentParser()

    arg_parser.add_argument('repo_loc',type=Path)

    arg_parser.add_argument('--search_terms',nargs='+')
    
    # Not yet implemented, TODO
    # arg_parser.add_argument('--regex',action='store_true')
    
    if debug:

        return arg_parser.parse_args(['TEST VAL TODO: REPLACE WITH USABLE VALUE'])

    else:

        return arg_parser.parse_args()

def main(prog_args):
    
    try:
        
        results = {}
        
        for term in prog_args.search_terms:
            
            results[term] = list(yield_results(prog_args,term))
        
        print(json.dumps(results,indent=4))
        
    except Exception as e:

        traceback.print_exc()
        
if __name__ == "__main__":
    
    # This is required for using PyInstaller to convert a script
    # using multiprocessing into an .exe
    freeze_support()
    
    prog_args = gather_args()

    main(prog_args)