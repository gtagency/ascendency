angular.module('game', ['gameServices', 'ui.bootstrap']).config(['$routeProvider', function($routeProvider) {
    // TODO: user page
    // TODO: Agent page
    // TODO: View match
    // match page
    $routeProvider
    .when('/agents/:filter', {templateUrl: 'views/agentlist.html', controller: AgentListCtrl})
    .when('/agent/:agentId', {templateUrl: 'views/agent.html', controller: AgentCtrl})
    .when('/matches/:filter', {templateUrl: 'views/matchlist.html', controller: MatchListCtrl})
    .when('/match/:matchId', {templateUrl: 'views/match.html', controller: MatchCtrl})
    .when('/user/login', {templateUrl: 'views/login.html', controller: UserCtrl})
    .when('/user/register', {templateUrl: 'views/register.html', controller: UserCtrl})
    // FIXME: this should probably be replaced with a 404 page or something
    .otherwise({templateUrl: 'views/home.html', controller: HomeCtrl});

}]);
