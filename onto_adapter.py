from chatterbot.logic import LogicAdapter
from chatterbot.conversation import Statement
from random import uniform
from rdflib import Graph
from rdflib import URIRef
from parse import parse
from tqdm import tqdm
import requests
from filesystem import file_exists
from filesystem import makedirs


class OntoAdapter(LogicAdapter):

    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.ontology = Graph()
        self.load_schema()

    @staticmethod
    def download_schema(schema_file, url):
        # TODO refactor into more general download methods
        if not file_exists(schema_file):
            makedirs(schema_file.split("/")[0])
            response = requests.get(url, stream=True)
            # shamelessly stolen from https://stackoverflow.com/a/10744565
            with open(schema_file, "wb") as handle:
                for data in tqdm(response.iter_content()):
                    handle.write(data)

    def load_schema(self):
        schema_file = "schema-org/schema.nt"
        url = "http://schema.org/version/latest/schema.nt"

        self.download_schema(schema_file, url)

        self.ontology.parse(schema_file, format="nt")

    def load_schema_for_type(self, type):
        schema_file = "schema-org/{type}.nt"
        url = "https://schema.org/{type}.nt"

        self.download_schema(schema_file, url)

        self.ontology.parse(schema_file, format="nt")

    def parse_input(self, statement_text):
        results = parse("{instance} is a {object}", statement_text)
        if results is None:
            return None
        return results.named

    def can_process(self, statement):
        results = self.parse_input(statement.text)
        if results is None:
            return False
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

        def print_values(what, values):
            print(what)
            if values is not None:
                for list_value in list(values):
                    print("\t", list_value)
            print("\r")

        import random

        # Randomly select a confidence between 0 and 1
        confidence = uniform(0, 1)

        parsed = self.parse_input(input_statement.text)

        object_uri = URIRef("http://schema.org/{}".format(parsed["object"]))
        domain_includes_uri = URIRef("http://schema.org/domainIncludes")

        # self.load_schema_for_type(parsed["object"])
        # property = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#Property")
        print("object_uri", object_uri)

        for subject in self.ontology.subjects(domain_includes_uri, object_uri):
            subject_uri = URIRef(subject)

            subject_label = (list(self.ontology.preferredLabel(subject_uri)))
            subject_comment = self.ontology.comment(subject_uri)
            print("\t", subject, subject_label, subject_comment)

        try:
            # print_values("domainIncludes", self.ontology.subjects(domain_includes_uri, object_uri))
            pass
        except:
            # eat it for now
            pass

        # For this example, we will just return the input as output
        selected_statement = Statement(text = "What is {}?".format(parsed["instance"]))
        selected_statement.confidence = confidence

        return selected_statement
