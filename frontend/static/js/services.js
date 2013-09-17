angular.module('gameServices', ['ngResource']).
    factory('User', function($resource) {
        return $resource('users', {}, {
            // default Angular factory
        });
    }).factory('Match', function($resource) {
        return $resource('matches/:matchId', {}, {
            // default Angular factory
        });
    });
    // TODO: User factory
    // TODO: Agent factory
