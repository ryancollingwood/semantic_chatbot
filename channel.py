from abc import abstractmethod
from events import Event
from pubsub import pub


class Channel(object):
    def __init__(self):
        pub.subscribe(self.display, Event.info)
        pub.subscribe(self.get_input, Event.get_input)
        pub.subscribe(self.confirm_valid_response, Event.confirm_valid_response)
        pub.subscribe(self.teach_valid_response, Event.teach_valid_response)
        pub.subscribe(self.display_valid_response, Event.display_valid_response)

    @abstractmethod
    def get_input(self, prompt):
        pass

    @staticmethod
    @abstractmethod
    def response_is_valid(input_statement, response):
        pass

    @abstractmethod
    def teach_valid_response(self, input_statement):
        pass

    @abstractmethod
    def confirm_valid_response(self, response, input_statement):
        pass

    @abstractmethod
    def display(self, message):
        pass

    @staticmethod
    @abstractmethod
    def display_valid_response(response):
        pass
