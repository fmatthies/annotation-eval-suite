FROM continuumio/miniconda3

ENTRYPOINT [ "/bin/bash", "-c" ]

WORKDIR /annotation-eval-suite

ADD . /annotation-eval-suite
RUN conda env create -f /annotation-eval-suite/annotation-eval-suite.yml

EXPOSE 5000

CMD [ "source activate annotation-eval-suite && exec python run.py" ]