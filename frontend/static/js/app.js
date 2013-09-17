angular.module('game', ['gameServices']).config(['$routeProvider', function($routeProvider) {
    // TODO: user page
    // TODO: login page
    // TODO: register page
    // TODO: Agent page
    // TODO: Current matches
    // match page
    $routeProvider
    .when('/matches/:matchId', {templateUrl: 'views/games.html', controller: MatchCtrl})
    .when('/test', {templateUrl: 'views/home.html', controller: HomeCtrl})
    .otherwise({redirectTo: '/test'});

}]);
