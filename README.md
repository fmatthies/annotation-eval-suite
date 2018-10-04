# annotation-viewer
This little program provides some utilities for visualizing and calculating Inter-Annotator Agreement Scores
 in annotation tasks. As of now, the program needs `brat` [1] annotated files and only regards `triggers`.

## Setup
### Docker
Using `docker` will circumvent any dependency issues (first and foremost under Windows) you'll probably encounter otherwise. The repository contains a `docker build file`; the steps to get it running are as follows:  
**Linux**:  
- Build the image from the docker file (with e.g. NAME as "annotation-eval-suite"):
```
sudo docker build -t NAME .
```
- Create and run a container from the image (with e.g. PORT_ON_LOCAL as "5000" as well, PATH_TO_ROOT_FOLDER_OF_FILES as the path to the files you want to analyze and NAME as the same name you choose in the previous step):
```
sudo docker run -p PORT_ON_LOCAL:5000 -t -d -v PATH_TO_ROOT_FOLDER_OF_FILES:/annotation-eval-suite/resources NAME
```
At this point you should have a `docker` container up and runnning (`sudo docker ps` lists all running containers) and the suite should be accessible from `http://0.0.0.0:PORT_ON_LOCAL`. When giving a path for a root folder (c.f. "Usage"), your root folder is now `/annotation-eval-suite/resources` (as specified with the `-v` flag from the `docker run` command).  

ToDo:
```
docker stop
docker start
```

### Basic
**Linux**:  
Create a `conda` [2] environment from the `annotation-viewer.yml` file with  
`conda env create -f annotation-viewer.yml`
This should create an environment with the name `annotation-eval-suite` (`conda info --envs` lists all environments).

When in your `conda` environment (`conda activate annotation-eval-suite` OR `source activate annotation-eval-suite`), start a local standalone server of the program with
`python run.py`
The viewer is then accessible from `http://0.0.0.0:5000`

**Windows**:
Manually remove all dependencies from `annotation-viewer.yml` that are unavailable under Windows (`conda` will give you a list when you try creating the environment, cf. Linux setup).
Activate the new `conda` environment in CMD (`activate conda`) and start the server (`python run.py`).

## Usage
When prompted for a root folder, the program assumes the following structure
(where the `".ann"` files are `brat` conform files):  
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
If you want only specific documents from your collection to be considered, use an index file with the names
of the documents (one per line without file ending). This file has to be named `"index"`.  
If no such file is given or should be used, the **union** of all documents of all annotators is used.

If you want only specific annotators to be included, fill out the respective field
with a comma separated string of annotator names:  
`annotator01, annotator03, ...`

After that, the program should be self-explanatory. You can cycle through documents
and their sentences that have at least one annotation across all annotators. Furthermore you can see a table
or the inter annotator agreements of the respective document.  
The measurements you can choose are `"strict", "approximate", "one vs. all"`.
The first two calculate the average over all annotators in a one vs. one set up.
the last uses a centroid approach [3] and you can choose `threshold` and `boundary` values.

## Upcoming Features
- also allow for `".a1"` and `".a2"` input files
- tooltips
- different input formats
- [...]

and  

- `please request via issues`

## References
[1] http://brat.nlplab.org/  
[2] https://conda.io/  
[3] Lewin, I., Kafkas, S., & Rebholz-Schuhmann, D. (2012). Centroids: Gold standards with distributional variation. In LREC(pp. 3894-3900).

