import os.path
import json

from ovos_number_parser import extract_number
from ovos_workshop.skills.game_skill import ConversationalGameSkill


class MyGameSkill(ConversationalGameSkill):
    def __init__(self, *args, **kwargs):
        game_image = os.path.join(os.path.dirname(__file__), "resources", "images", "game.png")
        super().__init__(skill_voc_filename="Interactive_story_keyword", # <- the game name so it can be started
                         skill_icon=game_image,
                         game_image=game_image,
                         *args, **kwargs)
        
        self.episode_data = None
        self.episode_number = 0
        self.number_of_episodes = 0

        self.current_room = None
        self.listen_to_player_utterance = False

        # We don't need this at all. I keep this around for fast debuging
        # self.gui.show_text(f"{selfdata}")

# <editor-fold desc="setups">
    def on_play_game(self):
        """called by ocp_pipeline when 'play XXX' matches the game"""
        self.get_episodes()


    def get_episodes(self):
        self.number_of_episodes = sum(1 for _, _, files in os.walk(f'{self.root_dir}/resources/episodes') for f in files)

        self.select_episode()

    def select_episode(self):
        if  (self.number_of_episodes == 1):
            self.speak_dialog("single_episode_found")
            self.open_json_file(1)
        else:
            # chosen_episode = self.ask_selection(chosen_episode)
            self.speak_dialog("number_of_episodes_found", {"number_of_episodes":self.number_of_episodes})
            self.select_episode_from_multiple()

    def select_episode_from_multiple(self):
        self.speak_dialog('ask_for_episode_to_play', expect_response=True)
        chosen_episode_input = self.get_response('Welke aflevering wil je spelen?')
        #In some languages lower numbers will return the written text instead of a numeral
        #The extract_number will take the string and extract a number from it if possible
        chosen_episode = extract_number(chosen_episode_input, ordinals=True, lang=self.lang)

        #There was no number in the player response, repeat the question
        if chosen_episode == False:
            self.speak_dialog("no_number")
            self.select_episode_from_multiple()
        else:
            chosen_episode_int = int(chosen_episode)
            if chosen_episode_int <= 0 or chosen_episode_int > self.number_of_episodes:
                self.speak_dialog("episode_not_found", wait=True)
                self.speak_dialog("ask_for_valid_episode", {"episode_number":self.number_of_episodes})
                self.select_episode_from_multiple()
            else:
                self.open_json_file(chosen_episode_int)

    def open_json_file(self, chosen_episode_int):
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
        self.speak(f"{room['description']}")
        
    def reset_episode(self):
        self.current_room = self.episode_data['rooms']['start']

    def ask_question(self, room):
        self.speak(f"{room['question']}", wait=True, expect_response=True)
        self.listen_to_player_utterance = True

    def main_game_loop(self):
        current_room = self.current_room
        if 'end' not in current_room:
            self.show_room(current_room)
            self.ask_question(current_room)

        if 'end' in current_room:
            self.end_of_path(current_room)

    def end_of_path(self, current_room):
        self.show_room(current_room)
        ending_type = current_room['end']

        #The player failed
        if (ending_type == "fail"):
            self.speak("game over", wait=True)
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
            self.speak("Je hebt gewonnen", wait=True)
            if (self.episode_number == self.number_of_episodes):
                #We beat the game, quiting
                self.speak("Je hebt het seizoen voltooid. Goed gedaan!", wait=True)
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
                        

#</editor-fold>

    def on_stop_game(self):
        """called when game is stopped for any reason
        auto-save may be implemented here"""
        self.speak("game ended")

    def on_game_command(self, utterance: str, lang: str):
        """pipe user input that wasnt caught by intents to the game
        do any intent matching or normalization here
        don't forget to self.speak the game output too!
        """

        if (self.listen_to_player_utterance == True and utterance):

            # self.speak(f"{utterance}", wait=True) 

            choices = self.current_room.get("choises", {})

            # Iterate through each choice and its keywords
            for room_name, details in choices.items():
                
                # self.log.debug(details)
                if utterance in (keyword.lower() for keyword in details["keywords"]):
                    # Return the name of the room if a match is found
                    self.current_room = self.episode_data['rooms'][room_name]
                    self.listen_to_player_utterance = False
                    self.main_game_loop()


    def on_abandon_game(self):
        """user abandoned game mid interaction

        auto-save is done before this method is called
        (if enabled in self.settings)

        on_game_stop will be called after this handler"""
        self.speak("abandoned game")

