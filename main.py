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
        """
        Chatbot for semantic reasoning
        :param name: Display name for the bot
        :param confidence_query_threshold: If a response to an input to is below this threshold we may need instruction
        :param seed_if_empty: If the bot doesn't have anything in it's database should be import some test data?
        """
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
                    'import_path': 'onto_adapter.OntoAdapter'
                },
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
        """
        Subscribe/Unsubscribe to events of interest to the bot
        :param is_ready:
        :return:
        """
        self.is_ready = is_ready

        if is_ready:
            pub.subscribe(self.receive_input_statement, Event.received_input)
            pub.subscribe(self.received_teach_valid_response, Event.received_teach_valid_response)
            pub.subscribe(self.receive_response_is_valid, Event.response_is_valid)
        else:
            # TODO unsubscribe
            pass

    def train(self):
        """
        Import seed data
        :return:
        """

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
        """
        Send a message that we're ready for questions
        May not be required in a true messaging environment once we're out of CLI land
        :param prompt:
        :return:
        """
        pub.sendMessage(Event.get_input, prompt = prompt)

    def receive_input_statement(self, input_text: str):
        """
        For the `input_text` try to find a response.
        - If the response exceeds our confidence threshold then display it.
        - If the response is below our confidence threshold then ask if it's a valid response, resulting in either:
            - Confirmation and we record the confirmation
            - Another response is provided and is recorded
        - If there is no response we will ask for one, resulting in either:
            - If a response is given we record it as a valid response for the input
            - If no response is given we don't record anything discarding the input
        :param input_text:
        :return:
        """
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

    def received_teach_valid_response(self, input_text: str, input_statement: Statement):
        """
        We've been taught a new valid response
        :param input_text:
        :param input_statement:
        :return:
        """
        correct_response = self.get_input_statement(input_text)

        if correct_response.text != "":
            self.receive_response_is_valid(input_statement, correct_response)
            pub.sendMessage(Event.info, message = "Response added to database.")

    def receive_response_is_valid(self, input_statement: Statement, response: Statement):
        """
        We've received confirmation that an existing response is valid
        :param input_statement:
        :param response:
        :return:
        """
        self.bot.learn_response(response, input_statement)
        pub.sendMessage(Event.info, message="Confirmed response.")

    def get_input_statement(self, input_text: str, conversation: str = None) -> Statement:
        """
        For the `input_text` create a statement for use in other functions
        :param input_text:
        :param conversation:
        :return:
        """
        search_text = self.bot.storage.tagger.get_bigram_pair_string(
            input_text
        )

        return Statement(
            text=input_text,
            search_text=search_text,
            conversation=conversation,
        )


class TerminalChannel(Channel):

    def __init__(self):
        super(TerminalChannel, self).__init__()

    @staticmethod
    def input(prompt: str, event_to_raise: str = None) -> str:
        """
        Get input from the terminal and optionally raise an event
        :param prompt:
        :param event_to_raise:
        :return:
        """
        print(prompt)
        input_text = input(">")
        if event_to_raise is not None:
            pub.sendMessage(event_to_raise, input_text = input_text)
        return input_text

    def get_feedback(self) -> bool:
        """
        Get confirmation, this will loop until we either get a yes or a no
        :return:
        """
        text = input()

        if 'yes' in text.lower():
            return True
        elif 'no' in text.lower():
            return False
        else:
            print('Please type either "Yes" or "No"')
            return self.get_feedback()

    def get_input(self, prompt: str):
        """
        Get our input from the user and raise appropriate event with the chatbot
        :param prompt:
        :return:
        """
        self.input(prompt, Event.received_input)

    @staticmethod
    def response_is_valid(input_statement: Statement, response: Statement):
        """
        Tell the bot the `response` is valid for the `input_statement`
        :param input_statement:
        :param response:
        :return:
        """
        pub.sendMessage(Event.response_is_valid, input_statement = input_statement, response = response)

    def confirm_valid_response(self, response: Statement, input_statement: Statement):
        """
        Get confirmation that the `response` is valid for the `input_statement`

        May be interesting to work out in non-CLI environments
        :param response:
        :param input_statement:
        :return:
        """
        print(f'\nIs "{response.text}" a coherent response to "{input_statement.text}"?')

        if self.get_feedback():
            self.response_is_valid(input_statement, response)
        else:
            self.teach_valid_response(input_statement)

    def display(self, message: str):
        """
        Display a message, may need to extended this for multi-user environments
        :param message:
        :return:
        """
        print(message)

    def teach_valid_response(self, input_statement: Statement):
        """
        Ask for instruction about an `input_statement`
        :param input_statement:
        :return:
        """
        input_text = self.input(f"teach me about: {input_statement.text}")
        pub.sendMessage(Event.received_teach_valid_response, input_text = input_text, input_statement = input_statement)

    @staticmethod
    def display_valid_response(response: Statement):
        """
        Display the response, knowing that it is valid
        :param response:
        :return:
        """
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
