import os.path
import json

from ovos_number_parser import extract_number
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills.game_skill import ConversationalGameSkill
from ovos_workshop.decorators import layer_intent, enables_layer, disables_layer, resets_layers


class MyGameSkill(ConversationalGameSkill):
    def __init__(self, *args, **kwargs):
        game_image = os.path.join(os.path.dirname(__file__), "resources", "images", "spell-book.png")
        super().__init__(skill_voc_filename="Interactive_story_keyword", # <- the game name so it can be started
                         skill_icon=game_image,
                         game_image=game_image,
                         *args, **kwargs)
        
        self.episode_data = None
        self.episode_number = 0
        self.number_of_episodes = 0

        self.current_room = None
        self.listen_for_player_input = False
        self.listen_for_episode_number = False

        self.rooms_to_remember = set()

        #debugging
        # We don't need this at all. I keep this around for fast debuging
        # self.gui.show_text(f"{selfdata}")
        self.debug_mode = False

        def initialize(self):
            # start with all game states disabled
            self.intent_layers.disable()
            self.gui.show_text("initialize")
            


# <editor-fold desc="setups">
    def on_play_game(self):
        """called by ocp_pipeline when 'play XXX' matches the game"""
        self.intent_layers.disable()
        self.get_episodes()

    @enables_layer(layer_name="stop_game")
    def get_episodes(self):
        self.number_of_episodes = sum(1 for _, _, files in os.walk(f'{self.root_dir}/resources/episodes') for f in files)
        self.select_episode()

    @enables_layer(layer_name="testing")
    def select_episode(self):
        if  (self.number_of_episodes == 1):
            self.speak_dialog("single_episode_found")
            self.open_json_file(1)
        else:
            # chosen_episode = self.ask_selection(chosen_episode)
            self.speak_dialog("number_of_episodes_found", {"number_of_episodes":self.number_of_episodes})
            self.speak_dialog("ask_for_episode_to_play", expect_response=True)
            self.listen_for_episode_number = True

    def select_episode_from_multiple(self, chosen_episode_input):
        #In some languages lower numbers will return the written text instead of a numeral
        #The extract_number will take the string and extract a number from it if possible
        chosen_episode = extract_number(chosen_episode_input, ordinals=True, lang=self.lang)

        #There was no number in the player response, repeat the question
        if chosen_episode == False:
            self.speak_dialog("no_number")
            self.speak_dialog("ask_for_valid_episode", {"episode_number":self.number_of_episodes}, expect_response=True)
        else:
            chosen_episode_int = int(chosen_episode)
            if chosen_episode_int <= 0 or chosen_episode_int > self.number_of_episodes:
                self.speak_dialog("episode_not_found")
                self.speak_dialog("ask_for_valid_episode", {"episode_number":self.number_of_episodes}, expect_response=True)
            else:
                self.open_json_file(chosen_episode_int)

    def open_json_file(self, chosen_episode_int):
        self.listen_for_episode_number = False

        self.episode_number = chosen_episode_int

        self.speak_dialog("start_episode", {"episode_number":chosen_episode_int}) 
        
        # Opening JSON file
        f = open(f'{self.root_dir}/resources/episodes/Episode{chosen_episode_int}_Data.json')

        # returns JSON object as a dictionary
        self.episode_data = json.load(f)

        # Closing file
        f.close()

        self.reset_episode()
        self.main_game_loop()

#</editor-fold>

# <editor-fold desc="main game logic">

    def show_room(self, room):
        if 'audio_file' in room:
            self.play_audio(f"{self.root_dir}/resources/audio/{room['audio_file']}", wait=True)
        else:
            self.speak(f"{room['description']}", wait=True)

    def reset_episode(self):
        self.current_room = self.episode_data['rooms']['start']
        self.rooms_to_remember.clear()

    def ask_questions(self, room):
        current_question_option = 0

        choices = room.get("choices", {})

        for room_name, details in choices.items():
            current_question_option+=1
            if current_question_option == len(choices): 
                self.speak_dialog("final_option")
                self.speak(details["question_item"], wait=1, expect_response=True)
            else: self.speak(details["question_item"], wait=2)

        # num_retries=0
        self.listen_for_player_input = True



    def main_game_loop(self):
        current_room = self.current_room
        if 'end' not in current_room:
            self.show_room(current_room)

            if 'remember_room' in current_room:
                # Get the current room name (self.current_room should be a dictionary inside self.episode_data['rooms'])
                current_room_name = next((name for name, data in self.episode_data['rooms'].items() if data == self.current_room), None)
                self.rooms_to_remember.add(current_room_name)

            if 'skip_to_room' in current_room:
                self.change_rooms(current_room['skip_to_room'])

            elif 'room_remember_check' in current_room:
                condition_data = current_room.get("room_remember_check", {})
                room_condition_met = False
                #Check if the player has visited a certain room before
                for room in self.rooms_to_remember:
                    if (room == condition_data['room_to_remember']):
                        room_condition_met = True
                        self.change_rooms(condition_data['true'])
                        break
                #Stop the skill from going to the false room if the room condition has been met
                if (room_condition_met == False): self.change_rooms(condition_data['false'])
                

            else:
                self.ask_questions(current_room)

        if 'end' in current_room:
            self.end_of_path(current_room)


    def change_rooms(self, new_room):
        self.current_room = self.episode_data['rooms'][new_room]
        self.main_game_loop()


    def end_of_path(self, current_room):
        self.show_room(current_room)
        ending_type = current_room['end']

        #The player failed
        if (ending_type == "fail"):
            self.speak_dialog("game_over", wait=True)
            #Try again
            if (self.ask_yesno("Wil je het opnieuw proberen?") == 'yes'):
                self.reset_episode()
                self.main_game_loop()
            else:
                #The player didn't want to replay the episode and there are no other epsidoes to play. Quit
                if (self.episode_number == self.number_of_episodes):
                    self.on_stop_game()

                else:
                    #The player want's to play another epsidoe
                    if (self.ask_yesno("Wil je een andere aflevering spelen?") == 'yes'):
                        self.get_episodes()

        elif (ending_type == "win"):
            self.speak_dialog("win_game", wait=True)
            if (self.episode_number == self.number_of_episodes):
                #We beat the game, quiting
                self.speak_dialog("season_complete", wait=True)
                self.speak_dialog("congratulations")
                self.on_stop_game()

            else:
                if (self.ask_yesno("Wil je de volgende aflevering spelen?") == "yes"):
                    #play the next epsiode
                    self.open_json_file(self.episode_number + 1)

                else:
                    if (self.ask_yesno("Wil je een andere aflevering spelen?") == "yes"):
                        #THe player wants to go to the level selection
                        self.get_episodes()
                    
                    else:
                        #The player quits
                        self.on_stop_game()


    @resets_layers()
    def handle_game_over(self):
        self.speak_dialog("game_ended")
        # self.speak_dialog("stop.game")
        self._playing.clear()
        self._paused.clear()
                        

#</editor-fold>

# <editor-fold desc="GameSkill logic">

    def on_stop_game(self):
        """called when game is stopped for any reason
        auto-save may be implemented here"""
        self.handle_game_over()
        

    def on_game_command(self, utterance: str, lang: str):
        """pipe user input that wasnt caught by intents to the game
        do any intent matching or normalization here
        don't forget to self.speak the game output too!
        """

        if (self.debug_mode == True):
            self.gui.show_text(f"{utterance}")
        # utterance.lower().strip()
        # self.gui.show_text(f"{utterance}")

        if (self.listen_for_episode_number == True and utterance):
            self.select_episode_from_multiple(utterance)


        if (self.listen_for_player_input == True and utterance):

            keyword_matched = False

            choices = self.current_room.get("choices", {})

            # Iterate through each choice and its keywords
            for room_name, details in choices.items():

                # self.log.debug(details)
                if any(keyword in utterance.lower().strip() for keyword in (kw.lower() for kw in details["keywords"])):

                    keyword_matched = True

                    if 'transition_text' in details:
                        self.speak(details["transition_text"])

                    self.listen_for_player_input = False

                    # Return the name of the room if a match is found
                    self.change_rooms(room_name)

                    break
            # if keyword_matched == False:
            #     self.speak_dialog("invalid_keyword")
            #     self.speak_dialog("ask_for_repeat", expect_response=True)


    def on_abandon_game(self):
        """user abandoned game mid interaction

        auto-save is done before this method is called
        (if enabled in self.settings)

        on_game_stop will be called after this handler"""
        self.speak("abandoned game")
        self.handle_game_over()

#</editor-fold>


# <editor-fold desc="Debugging">

    @layer_intent(
        IntentBuilder("TestInteractiveStorySkillIntent").
        require("testKeyword"),
        layer_name="testing")
    def test_intent(self):
        self.gui.show_text(f"{self.rooms_to_remember}")


#</editor-fold>