import random

from .effects import effects

class NoCardException(BaseException): pass
class ActionException(BaseException): pass
class SetupException(BaseException): pass

class GameState(object):

    def __init__(self, cards, player_count, initial_deck):
        self.cards = []
        self.trash = []

        for card in cards.keys():
            self.cards.extend([card] * cards[card])

        self.players = [Player(self, initial_deck) for i in range(player_count)]

    def take_card(self, name):
        for card in self.cards:
            if card.name == name:
                self.cards.remove(card)
                return card
        raise NoCardException

    def return_card(self, card):
        self.cards.append(card)

    def trash_card(self, card):
        self.trash.append(card)

class Player(object):

    def __init__(self, game, initial_deck):
        self._game = game
        
        self.hand = []
        self.in_play = []
        self.deck = []
        self.discard = []
        self.victory = 0

        self.current_treasure = 0
        self.current_actions = 0
        self.current_buys = 0

        # set up initial deck
        for card_name in inital_deck:
            try:
                self.deck.append(self._game.take_card(card_name))
            except NoCardException:
                raise SetupException
        random.shuffle(self.deck)

    def do_start_phase(self):
        self.current_treasure = 0
        self.current_actions = 1
        self.current_buys = 1

        for i in range(5):
            self.draw()

    def draw(self):
        
        if len(self.deck) == 0 and len(self.discard) > 0:
            # shuffle discard into deck
            random.shuffle(self.discard)
            self.deck.extend(self.discard)
            self.discard = []

        if len(self.deck) > 0:
            # draw from deck
            self.hand.append(self.deck.pop(0))

    @property
    def can_do_action(self):
        return (self.current_actions > 0)

    def do_action(self, card_name):
        for card in self.hand:
            if card.name == card_name:
                if not card.is_action:
                    raise ActionException, 'card is not an action card'

                # perform card action
                card.activate_effect(self._game, self)

                # put card into play
                self.hand.remove(card)
                self.in_play.append(card)

                return
                
        raise NoCardException

    @property
    def can_do_buy(self):
        return (self.current_buys > 0)
    
    def do_buy(self, card_name):
        card = self._game.take_card(card_name)

        if card.price > self.current_treasure:
            self._game.return_card(card)
            raise ActionException, 'insufficient funds'

        self.current_treasure -= card.price
        self.discard.append(card)
        self.current_actions = 0 # prevent further actions

    def do_clean_phase(self):
        self.discard.extend(self.hand)
        self.discard.extend(self.in_play)
        self.hand = []
        self.in_play = []

class Card(object):

    def __init__(self, type, name, price, 
                 treasure=0, victory_pts=0, effects=None):
        self.type = type
        self.name = name
        self.price = price
        self.is_action = (effects is None)
        self.treasure = treasure
        self.victory_pts = victory_pts
        self.effects = effects

    def gain_effect(self, game, player):
        """Effect of buying or otherwise gaining this card."""
        player.victory += self.victory_pts

    def loss_effect(self, game, player):
        """Effect of removing this card from play."""
        player.victory -= self.victory_pts

    def draw_effect(self, game, player):
        """Effect of having this card in a hand."""
        player.current_treasure += self.treasure

    def activate_effect(self, game, player, targets=None):
        """Effect of activating this card."""
        if targets is None:
            targets = {}
        targets = dict(targets)
        for effect in self.effects:
            if effect['name'] not in targets:
                targets[effect['name']] = None
        for effect in self.effects:
            name = effect['name']
            effects[name]['check'](effect, game, player, targets[name])
        for effect in self.effects:
            name = effect['name']
            effects[name]['perform'](effect, game, player, targets[name])

    @property
    def document(self):
        return {
            'type' : self.type,
            'name' : self.name,
            'price' : self.price,
            'treasure' : self.treasure,
            'victory_pts' : self.victory_pts,
            'effects' : self.effects
        }

def make_card(card_index, document):
    card_index[document['name']] = Card(**document)
    return card_index[document['name']]

def get_card(card_index, name):
    return card_index[name]
