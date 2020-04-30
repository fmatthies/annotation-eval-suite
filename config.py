# Streamlit Annotation Visualizer Configuration File
# for WebAnno Project Exports
#
# default tables in database: annotators, sentences, documents, annotation_types, layers
#
# default columns for entities: id, annotator, begin, end, text, sentence, document, type
# default columns for relations: id, annotator
#
# default indexed columns for entities: type, sentence
#
# default foreign keys for entities (cross table references):
#   annotator -> annotators (id),
#   sentence -> sentences (id),
#   type -> annotation_types (id)
#
# default foreign keys for relations (cross table references):
#   annotator -> annotators (id),
#
#
# all that is configured here is to be seen as an addition to the database structure

# ToDo: describe SQLite data types
additional_database_info = {
    "entities": {  # <- contains all actual annotations in WebAnno that coincide with one or more tokens
        "medication_entities": {  # <- key has to conform to a "layers" key
            "columns": {
                "list": "integer",
                "recommendation": "integer"
            },
            "indexed_columns": [],
            "reference_columns": {}
        },
        "medication_attributes": {  # <- key has to conform to a "layers" key
            "columns": {},
            "indexed_columns": [],
            "reference_columns": {}
        }
    },
    "relations": {  # <- contains relation annotations between entities
        "medication_relations": {  # <- key has to conform to a "layers" key
            "columns": {
                "entity": "text",
                "attribute": "text"
            },
            "indexed_columns": ["entity"],
            "reference_columns": {
                "entity": {  # <- name of the column for this table
                    "table": "medication_entities",  # <- name of the referenced table
                    "column": "id"  # <- name of the referenced column of the referenced table
                },
                "attribute": {
                    "table": "medication_attributes",
                    "column": "id"
                }
            }
        }
    }
}

# layers lists all annotation layers in the WebAnno project that should be used in the visualizer
layers = {
    "medication_entities": "webanno.custom.MedicationEntity",
    "medication_attributes": "webanno.custom.MedicationAttribute",
    "medication_relations": "webanno.custom.MedicationAttributeRelationTypeLink"
}
