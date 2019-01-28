from chatterbot import ChatBot
from chatterbot import comparisons, response_selection
from chatterbot.conversation import Statement
from chatterbot.trainers import ChatterBotCorpusTrainer
from channel import Channel
from filesystem import makedirs
from events import Event
from pubsub import pub


# Uncomment the following lines to enable verbose logging
# import logging
# logging.basicConfig(level=logging.INFO)


class SemanticChatBot(object):
    bot = None
    is_ready = False
    name = "bot"

    def __init__(self, name: str, confidence_query_threshold: float = 0.8, seed_if_empty = True):
        self.name = name
        self.confidence_query_threshold = confidence_query_threshold

        makedirs("./database")

        self.bot = ChatBot(
            name,
            storage_adapter='chatterbot.storage.SQLStorageAdapter',
            preprocessors=[
                'chatterbot.preprocessors.clean_whitespace',
                'chatterbot.preprocessors.unescape_html',
                'chatterbot.preprocessors.convert_to_ascii',
            ],
            logic_adapters=[
                {
                    "import_path": "chatterbot.logic.BestMatch",
                    "statement_comparison_function": comparisons.levenshtein_distance,
                    "response_selection_method": response_selection.get_first_response,
                    "default_response": "",
                }
            ],
            database_uri='sqlite:///database/database.db'
        )

        pub.sendMessage(Event.info, message = "Loading...")

        if seed_if_empty:
            if self.bot.storage.count() == 0:
                self.train()

        self.bot.read_only = True

        self.set_ready(True)

        pub.sendMessage(Event.info, message=f"Hello, my name is {self.name}")

    def set_ready(self, is_ready: bool):
        self.is_ready = is_ready

        if is_ready:
            pub.subscribe(self.receive_input_statement, Event.received_input)
            pub.subscribe(self.received_teach_valid_response, Event.received_teach_valid_response)
            pub.subscribe(self.receive_response_is_valid, Event.response_is_valid)
        else:
            # TODO unsubscribe
            pass

    def train(self):

        pub.sendMessage(Event.info, message = "Training, may take a while...")
        trainer = ChatterBotCorpusTrainer(self.bot)

        trainer.train(
            "chatterbot.corpus.english"
        )

        pub.sendMessage(Event.info, message = "exporting training data")

        makedirs("./output")
        trainer.export_for_training('./output/training_export.json')

        pub.sendMessage(Event.info, message = "Training complete.")

    @staticmethod
    def get_input(prompt: str):
        pub.sendMessage(Event.get_input, prompt = prompt)

    def receive_input_statement(self, input_text):
        input_statement = self.get_input_statement(input_text)
        # generate_response
        response = self.bot.get_response(
            input_statement
        )

        if response.text != "" or response.confidence > 0:
            if response.confidence >= self.confidence_query_threshold:
                pub.sendMessage(Event.display_valid_response, response = response)
            else:
                pub.sendMessage(Event.confirm_valid_response, input_statement = input_statement, response = response)
        else:
            pub.sendMessage(Event.teach_valid_response, input_statement = input_statement)

    def received_teach_valid_response(self, input_text, input_statement):
        correct_response = self.get_input_statement(input_text)

        if correct_response.text != "":
            self.receive_response_is_valid(input_statement, correct_response)
            pub.sendMessage(Event.info, message = "Response added to database.")

    def receive_response_is_valid(self, input_statement, response):
        self.bot.learn_response(response, input_statement)
        pub.sendMessage(Event.info, message="Confirmed response.")

    def get_input_statement(self, input_text, conversation = None):
        search_text = self.bot.storage.tagger.get_bigram_pair_string(
            input_text
        )

        if conversation is None:
            conversation = search_text

        return Statement(
            text=input_text,
            search_text=search_text,
            conversation=conversation,
        )


class TerminalChannel(Channel):

    def __init__(self):
        super(TerminalChannel, self).__init__()

    @staticmethod
    def input(prompt, event_to_raise = None):
        print(prompt)
        input_text = input(">")
        if event_to_raise is not None:
            pub.sendMessage(event_to_raise, input_text = input_text)
        return input_text

    def get_feedback(self):
        text = input()

        if 'yes' in text.lower():
            return True
        elif 'no' in text.lower():
            return False
        else:
            print('Please type either "Yes" or "No"')
            return self.get_feedback()

    def get_input(self, prompt):
        self.input(prompt, Event.received_input)

    @staticmethod
    def response_is_valid(input_statement, response):
        pub.sendMessage(Event.response_is_valid, input_statement = input_statement, response = response)

    def confirm_valid_response(self, response, input_statement):
        print(f'\nIs "{response.text}" a coherent response to "{input_statement.text}"?')

        if self.get_feedback():
            self.response_is_valid(input_statement, response)
        else:
            self.teach_valid_response(input_statement)

    def display(self, message):
        print(message)

    def teach_valid_response(self, input_statement):
        input_text = self.input(f"teach me about: {input_statement.text}")
        pub.sendMessage(Event.received_teach_valid_response, input_text = input_text, input_statement = input_statement)

    @staticmethod
    def display_valid_response(response):
        print(response.text)


def chat(name: str):
    terminal = TerminalChannel()
    semantic_bot = SemanticChatBot(name)

    while True:

        try:
            semantic_bot.get_input("I'm listening")

        # Press ctrl-c or ctrl-d on the keyboard to exit
        except (KeyboardInterrupt, EOFError, SystemExit):
            break


chat("Terminal")
