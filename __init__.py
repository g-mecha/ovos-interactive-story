import os.path

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

    def on_play_game(self):
        """called by ocp_pipeline when 'play XXX' matches the game"""
        # os.path.join(os.path.dirname(__file__), "res", "images", "game.png")
        self.number_of_episodes = sum(1 for _, _, files in os.walk(f'{self.root_dir}/resources/episodes') for f in files)
        self.gui.show_text(f"{self.number_of_episodes}")

        # select_episode(number_of_episodes)
        

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

