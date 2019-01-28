from chatterbot.logic import LogicAdapter
from random import uniform
from rdflib import Graph
from rdflib import URIRef
from parse import parse

class OntoAdapter(LogicAdapter):

    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.ontology = Graph()
        self.ontology.parse("schema-org/schema.nt", format="nt")

    def parse_input(self, statement_text):
        results = parse("{instance} is a {object}", statement_text)
        return results.named

    def can_process(self, statement):
        results = self.parse_input(statement.text)
        if len(results) == 2:
            return True
        return False

    def get_labels(self, uri, predicate_string):
        graph = self.ontology
        predicate = URIRef(u'http://schema.org/' + predicate_string)
        name = URIRef(u'http://schema.org/name')
        object_list = []

        for obj in graph.objects(uri, predicate):
            label = obj
            if graph.value(obj, name):
                label = graph.value(obj, name)
            object_list.append(label)
        object_labels = ('\n'.join(object_list))

        return (object_labels)

    def process(self, input_statement, additional_response_selection_parameters):


        import random

        # Randomly select a confidence between 0 and 1
        confidence = uniform(0, 1)

        parsed = self.parse_input(input_statement.text)

        value = URIRef("http://schema.org/{}".format(parsed["object"]))
        print("value", value)
        print("labels", self.get_labels("type", parsed["object"]))
        labels = (list(self.ontology.preferredLabel(value)))

        try:
            print(list(self.ontology.subject_predicates(value)))
            print(list(self.ontology.predicate_objects(value)))
            print(list(self.ontology.subject_objects(value)))
            print(list(self.ontology.transitive_objects(value)))
            print(list(self.ontology.transitive_subjects(value)))
        except:
            # eat it for now
            pass

        # For this example, we will just return the input as output
        selected_statement = input_statement
        selected_statement.confidence = confidence

        return selected_statement
