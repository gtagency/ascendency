"""
Effect types that can be added to cards.
"""

def null_check(params, game, player, targets):
    pass

def add_buys_effect(params, game, player, targets):
    player.current_buys += params['count']

def add_actions_effect(params, game, player, targets):
    player.current_actions += params['count']

def add_treasure_effect(params, game, player, targets):
    player.current_treasure += params['count']

def draw_effect(params, game, player, targets):
    for i in range(params['count']):
        player.draw()

def trash_check(params, game, player, targets):
    if targets is None:
        raise ActionError, 'no targets specified'
    if len(targets) > params['count']:
        raise ActionError, 'too many targets'
    if 'type' in params and params['type'] is not None:
        if any(target.type != params['type'] for target in targets):
            raise ActionError, 'target of incorrect type'
    hand_copy = list(player.hand)
    for target_name in targets:
        for card in hand_copy:
            if card.name == target.name:
                hand_copy.remove(card)
                break
        raise ActionError, 'target not found in hand'

def trash_effect(params, game, player, targets):
    for target_name in targets:
        for card in player.hand:
            if card.name == target_name:
                player.hand.remove(card)
                card.loss_effect(game, player)
                game.trash.append(card)
                break

effects = {

    'add_buys' : { 
        'check' : null_check,
        'perform' : add_buys_effect
    },

    'add_actions' : {
        'check' : null_check,
        'perform' : add_actions_effect,
    },

    'add_treasure' : {
        'check' : null_check,
        'perform' : add_treasure_effect,
    },

    'draw' : {
        'check' : null_check,
        'perform' : draw_effect,
    },

    'trash' : {
        'check' : trash_check,
        'perform' : trash_effect,
    },

}

def register_effect(name, check, perform):
    if check is None:
        check = null_check
    effects[name] = { 'check' : check, 'perform' : perform }
