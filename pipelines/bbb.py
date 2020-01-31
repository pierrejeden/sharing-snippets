import os

input_repo_path = '/pfs/pipe-aaa'
input_folder = os.listdir(input_repo_path)[0]
input_folder_path = os.path.join(input_repo_path, input_folder)

input_files = sorted(os.listdir(input_folder_path))
print(f'found folder {input_folder} with files {input_files}')

latest_filename = input_files[-1]
latest_file_path = os.path.join(input_folder_path, latest_filename)
print(f'loading latest file: {latest_file_path}')

with open(latest_file_path, 'r') as f:
    latest_str = f.read()

print(f'content of latest file: {latest_str}')
