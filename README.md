# annotation-viewer

### Setup
**Linux**:  
Create a conda environment from the `annotation-viewer.yml` file with  
`conda env create -f annotation-viewer.yml -p PATH/TO/YOUR/CONDA_ENVS/FOLDER/ENV_NAME`

When in your conda environment (source activate ENV_NAME), start a local standalone server of the program with  
`python run.py`  
The viewer is then accessible from `http://127.0.0.1:5000`

### Usage
When prompted for a root folder, the program assumes the following structure (where the `".ann"` files are `brat` conform files):  
```
root
|
|--- < annotator01 >
|    |
|    |--- < doc01.txt >
|    |--- < doc01.ann >
|    |--- < doc02.txt >
|    |--- < doc02.ann >
|    |---     [...]
|
|--- < annotator02 >
|---     [...]
|
|--- index (optional)
```
If you want only specific documents from your collection to be considered, use an index file with the names of the documents (one per line without file ending). This file has to be named `"index"`.  
If no such file is given or should be used, the union of all documents of all annotators is used.

If you want only specific annotators to be included, fill out the respective field with a comma separated string of annotator names:  
`annotator01, annotator03, ...`

After that, the program should be self-explanatory. You can cycle through documents and their sentences that have at least one annotation across all annotators. Furthermore you can see a table for the inter annotator agreements of the respective document.  
The measurements you can choose are `"strict", "approximate", "one vs. all"`. The first two calculate the average over all annotators in a one vs. one set up. The last uses a centroid approach and you can choose `threshold` and `boundary` values.

### Upcoming Features
- also allow for `".a1"` and `".a2"` input files
- tooltips
- [...]

and  
`please request via issues`
