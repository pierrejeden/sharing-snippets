import os

input_repo_path = '/pfs/aaa-input'
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

out_folder_path = os.path.join('/pfs/out', input_folder)
latest_out_path = os.path.join(out_folder_path, latest_filename)

print(f'writing file {latest_out_path}')

try:
    with open(latest_out_path, 'w') as f:
        f.write(latest_str)
except Exception as e:
    print('failed to write, folder does not exist...')
    print(e)
    print('creating directory, writing again')
    os.mkdir(out_folder_path)
    with open(latest_out_path, 'w') as f:
        f.write(latest_str)
    print('write successful!')

new_file_name = 'new_' + latest_filename
new_file_out_path = os.path.join(out_folder_path, new_file_name)
print(f'adding another file {new_file_out_path}')
with open(new_file_out_path, 'w') as f:
    f.write(latest_str + '\nsome new content')

print('done!')
