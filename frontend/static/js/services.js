angular.module('gameServices', ['ngResource']).
    factory('User', function($resource) {
        return $resource('users', {}, {
            // default Angular factory
        });
    }).factory('Match', function($resource) {
        return $resource('matches/:matchId', {}, {
            // default Angular factory
        });
    }).factory('Agent', function($resource) {
        return $resource('agents/:agentId', {}, {
            // default Angular factory
        });
    }).factory('User', function($resource) {
        return $resource('users/:userId', {}, {
            // default Angular factory
        });
    });
