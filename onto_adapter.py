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

        # DEBUG Randomly select a confidence between 0 and 1
        confidence = uniform(0, 1)

        parsed = self.parse_input(input_statement.text)

        object_uri = URIRef("http://schema.org/{}".format(parsed["object"]))
        domain_includes_uri = URIRef("http://schema.org/domainIncludes")
        range_includes_uri = URIRef("http://schema.org/rangeIncludes")

        print("object_uri", object_uri)   

        chosen_object_subject = None

        for subject in self.ontology.subjects(domain_includes_uri, object_uri):
            subject_uri = URIRef(subject)
            subject_label = (list(self.ontology.preferredLabel(subject_uri)))
            if subject_label and len(subject_label) > 1:
                chosen_object_subject = subject_label[1]
            subject_comment = self.ontology.comment(subject_uri)

            # for input: "Avengers is a Move"
            # subject_label = [(rdflib.term.URIRef('http://www.w3.org/2000/01/rdf-schema#label'), rdflib.term.Literal('musicBy'))]
            print("\t", subject_label, subject_label, subject_comment)

            # for each of the subjects print out the expected types of the data
            for range_type in self.ontology.objects(subject_uri, range_includes_uri):
                range_uri = URIRef(range_type)
                range_label = (list(self.ontology.preferredLabel(range_uri)))
                range_comment = self.ontology.comment(range_uri)            
                print("\t\t", range_type, range_label, range_comment)                
                
        # For this example, we will just return the input as output
        if (subject_label):
            selected_statement = Statement(
                text = "What is {subject_label} for {instance}?".format(
                    subject_label = subject_label,
                    instance = parsed["instance"]
                    )     
                )
            selected_statement.confidence = confidence
        else:
            selected_statement =  Statement(
                text = "I'm sorry I don't know what sort of thing a '{instance}' is.".format(
                    instance = parsed["instance"]
                    )
                )
            selected_statement.confidence = 0
            
        return selected_statement
