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


DO_DEBUG = False

# TODO Generate a better output name
TOTAL_RESULTS = Path('.').joinpath('Git_Search_Results.json')

# TODO Add buffer for writing to file
# I.e. a list object that holds the output, 
# And another variable that says how many lines should be saved before saving the results to file.
# When the limit is reached, then the results are saved to file.



# This is required b/c multiprocessing.pool.Pool.apply_async doesn't play nice
# when passed a method that hasn't been imported. One way around this is to create
# a class and it pass it one of *those* methods.
class GitProcessor:

    @staticmethod
    def search_commit(tmp_dir,commit_hash,search_terms,repo_loc,*args,**kwargs):
        
        result_container = []

        try:
            
            for process_result in GitProcessor.yield_results(tmp_dir,commit_hash,search_terms,repo_loc):
                
                if process_result:
                    
                    result_container.append(process_result)

            if result_container:

                file_path = GitProcessor.generate_temp_file_path(tmp_dir)

                GitProcessor.write_results(result_container,file_path)

                return file_path, None
            
            else:
                
                return None, None

        except Exception as e:

            return None, e
        
    @staticmethod
    def yield_results(tmp_dir,commit_hash,search_terms,repo_loc):
        
        command = [
            'git',
            'grep',
            '--text',
            '--ignore-case',
            '--count',
            '--threads',
            '1'
        ]
        
        for idx, search_term in enumerate(search_terms):
            
            command.extend(['-e',f'"{search_term}"'])
            
            if idx != len(search_terms) - 1: command.append('--or')
            
        command.append(commit_hash)
        
        try:
            
            completed_result = subprocess.run(command,capture_output=True,text=True,cwd=repo_loc.absolute().__str__())
            
            completed_result.check_returncode()
            
            for result in completed_result.stdout.splitlines():
                
                yield result
            
        except Exception as e:
            
            if 'returned non-zero exit status 1.' not in str(e):
                
                print(str(e))
            
            # TODO
            yield None

    @staticmethod
    def generate_temp_file_path(tmp_dir,*args,**kwargs):
        """Generates a file name and path within the given temp dir.

        Args:
            tmp_dir (Path): The temporary directory path.

        Returns:
            Path: The generated file path.
        """

        while True:

            file_name = str(uuid.uuid4())

            file_path = Path(tmp_dir).joinpath(file_name)

            if not file_path.exists(): return file_path

    @staticmethod
    def write_results(result_container,file_path,*args,**kwargs):

        with open(file_path,'w+') as out_file:
            
            out_file.write(json.dumps(result_container))

def provide_output(prog_args,*args,**kwargs):
    
    num_results_found = len(open(TOTAL_RESULTS).readlines()) if TOTAL_RESULTS.exists() else 0
    
    print(f'{num_results_found} results found.')
    
    if num_results_found > 0:
    
        print(f'See {TOTAL_RESULTS.__str__()} for more info.')

def process_exception(future_exception,*args,**kwargs):
    
    if future_exception is not None:

        print(f'Exception while collecting future result: {str(future_exception)}')

def save_results(file_path,*args,**kwargs):

    new_content = json.loads(open(file_path).read())
    
    existing_results = json.loads(open(TOTAL_RESULTS).read()) if TOTAL_RESULTS.exists() else []
    
    existing_results.extend(new_content)
    
    with open(TOTAL_RESULTS,'w+') as out_file:
        
        out_file.write(json.dumps(existing_results,indent=4))

def yield_completed_futures(futures,*args,**kwargs):

    pbar = tqdm(total=len(futures),leave=False)

    sleep_time = 2

    while len(futures) > 0:

        futures_to_remove = []

        for future in futures:

            if future.ready():

                yield future

                futures_to_remove.append(future)

                pbar.update(1)

        for future in futures_to_remove:

            futures.remove(future)

        if len(futures) > 0:

            time.sleep(sleep_time)

    pbar.close()

def yield_commit_hashes(prog_args,*args,**kwargs):
    
    try:
    
        completed_process = subprocess.run([
            'git',
            'rev-list',
            '--all'],capture_output=True,text=True,cwd=prog_args.repo_loc.absolute().__str__())
        
        completed_process.check_returncode()
        
        for commit_hash in completed_process.stdout.splitlines():
            
            yield commit_hash
        
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
        
        if TOTAL_RESULTS.exists(): TOTAL_RESULTS.unlink()
        
        with tempfile.TemporaryDirectory() as tmp_dir:

            print(tmp_dir)

            with Pool() as pool:

                futures = []

                for commit_hash in yield_commit_hashes(prog_args):

                    # TODO Add other params as necessary
                    futures.append(pool.apply_async(GitProcessor.search_commit,(tmp_dir,commit_hash,prog_args.search_terms,prog_args.repo_loc)))
                    
                for future in yield_completed_futures(futures):

                    file_path, future_exception = future.get()

                    if file_path:

                        save_results(file_path)

                        file_path.unlink()

                    else:

                        process_exception(future_exception)

        provide_output(prog_args)

    except Exception as e:

        traceback.print_exc()
        
if __name__ == "__main__":
    
    # This is required for using PyInstaller to convert a script
    # using multiprocessing into an .exe
    freeze_support()
    
    prog_args = gather_args(debug=DO_DEBUG)

    main(prog_args)