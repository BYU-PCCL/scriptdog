import random
from scriptdog import Scriptdog, state_op, bind_op

# ============================================================
# SAMPLE FILE
#
# This python file shows a sample of how to write the python
# side of scriptdog. It links to the sample.dog script.
#
# The use case of this file is something like an Alexa Skill
# where the the loop in the if __name__ == "__main__" code
# represents what an AWS Lambda would be doing at each call
# since it is serverless. All you have to do is store the
# stack_obj and recover it at each step and that takes care
# of all state in your ScriptDog program.
# ============================================================


class SampleDog:
    def __init__(self, stack_obj):
        # set internal vars
        self.output = ""

        # ====================================
        # define functions for scriptdog

        @state_op  # state_op decorater attach to any particular variable
        def say(arg):
            arg = str(arg)
            if arg.startswith('"') and arg.endswith('"'):
                arg = arg[1:-1]
            self.output += arg + " "

        @bind_op  # bind_op decorater attach return value to a variable
        def get_flag():
            return random.choice([False, True])

        @bind_op  # bind_op decorater can also take parameters
        def get_value_based_on_flag(flag):
            if flag:
                return "TRUE FLAG"
            else:
                return "FALSE FLAG"

        # ====================================

        # create scriptdog obj
        self.dog = Scriptdog()

        # load the compiled (pkl) scriptdog script
        self.dog.load_program("compiled_scripts/sample.pkl")

        # bind all external python functions you want to call in
        # your scriptdog script
        self.dog.bind_function("say", say)
        self.dog.bind_function("get_flag", get_flag)
        self.dog.bind_function("get_value_based_on_flag",
                               get_value_based_on_flag)

        # hydrate the stack
        if not stack_obj:
            # init the stack for the first time
            self.dog.init_stack()
        else:
            # load a previously used stack
            self.dog.load_stack(stack_obj)

    def get_response(self, user_text):
        # to progress the scriptdog script until the
        # next expect statement, call step
        self.dog.step(user_text)
        return self.output.strip(), self.dog.stack_obj


if __name__ == "__main__":
    import readline
    import random

    stack_obj = None
    while True:
        utterance = input("> ")
        bot = SampleDog(stack_obj)
        output, stack_obj = bot.get_response(utterance)
        print(output)
