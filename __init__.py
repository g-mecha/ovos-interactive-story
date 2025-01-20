import os.path
import json

from ovos_number_parser import pronounce_number, extract_number
from ovos_workshop.skills.game_skill import ConversationalGameSkill


class MyGameSkill(ConversationalGameSkill):
    def __init__(self, *args, **kwargs):
        game_image = os.path.join(os.path.dirname(__file__), "resources", "images", "game.png")
        super().__init__(skill_voc_filename="GameName", # <- the game name so it can be started
                         skill_icon=game_image,
                         game_image=game_image,
                         *args, **kwargs)
        
        self.episode_data = None
        self.episode_number = 0
        self.number_of_episodes = 0

        # We don't need this at all. I keep this around for fast debuging
        # self.gui.show_text(f"{self.data}")


    def on_play_game(self):
        """called by ocp_pipeline when 'play XXX' matches the game"""
        # os.path.join(os.path.dirname(__file__), "res", "images", "game.png")
        self.number_of_episodes = sum(1 for _, _, files in os.walk(f'{self.root_dir}/resources/episodes') for f in files)

        self.select_episode()

    def select_episode(self):
        if  (self.number_of_episodes == 1):
            self.speak("Only 1 episode detected, playing episode 1")
            self.open_json_file(1)
        else:
            # chosen_episode = self.ask_selection(chosen_episode)
            self.speak(f"I found {self.number_of_episodes} episodes")
            chosen_episode_input = self.get_response('What episode do you want to play?')
            # chosen_episode self.extract_number
            chosen_episode = extract_number(chosen_episode_input, ordinals=True, lang=self.lang)

            self.gui.show_text(f"{chosen_episode_input}, {chosen_episode}")

            if chosen_episode == False:
                self.speak("Invalid. Please say a number")
                self.select_episode()
            else:
                chosen_episode_int = int(chosen_episode)
                if chosen_episode_int <= 0 or chosen_episode_int > self.number_of_episodes:
                    self.speak(f"Invalid input. Please select an episode between 1 and {self.number_of_episodes}")
                    self.select_episode()
                else:
                    self.speak(f"speel aflevering {chosen_episode_int}")
                    self.open_json_file(chosen_episode_int)

    def open_json_file(self, chosen_episode_int):
        
        # Opening JSON file
        f = open(f'{self.root_dir}/resources/episodes/Episode{chosen_episode_int}_Data.json')

        # returns JSON object as a dictionary
        self.episode_data = json.load(f)

        self.gui.show_text(f"{self.episode_data['rooms']['start']}")

        # Closing file
        f.close()
        

    def on_stop_game(self):
        """called when game is stopped for any reason
        auto-save may be implemented here"""
        self.speak("game ended")

    def on_game_command(self, utterance: str, lang: str):
        """pipe user input that wasnt caught by intents to the game
        do any intent matching or normalization here
        don't forget to self.speak the game output too!
        """
        print(f"user game input: {utterance}")
        answer = "the game has spoken"
        self.speak(answer, wait=True, expect_response=True)

    def on_abandon_game(self):
        """user abandoned game mid interaction

        auto-save is done before this method is called
        (if enabled in self.settings)

        on_game_stop will be called after this handler"""
        self.speak("abandoned game")

