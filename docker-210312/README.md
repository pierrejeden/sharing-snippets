## Output of committing 1.txt and the 2.txt:

logs of first pipeline: two files found after the second commit.
```
found folder X with files ['1.txt', '2.txt']
loading latest file: /pfs/aaa-input/X/2.txt
content of latest file: file 2

writing file /pfs/out/X/2.txt
failed to write, folder does not exist...
[Errno 2] No such file or directory: '/pfs/out/X/2.txt'
creating directory, writing again
write successful!
adding another file /pfs/out/X/new_2.txt
done!
```

logs of second pipeline: only the two latest files found, not the previously committed `['2.txt', 'new_2.txt']`...
```
found folder X with files ['2.txt', 'new_2.txt']
loading latest file: /pfs/pipe-aaa/X/new_2.txt
content of latest file: file 2

```
