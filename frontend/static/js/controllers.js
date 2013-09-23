function HomeCtrl($scope) {
};

function NavCtrl($scope) {
    $scope.navigate = function(uri) {
        window.location.hash = uri;
    }
};

function UserCtrl($scope, User) {

    $scope.user = null;
    $scope.input = {};

    $scope.login = function() {
        var data = {
            username: $scope.input.username,
            password: $scope.input.password
        }
         
        // FIXME: Don't send passwords in plaintext
        User.get(data, function(response) {
            $scope.user = response;
            // TODO: show login errors
        }, function(response) {
            // post failed
        });
    }

    $scope.logout = function() {
        $scope.user = null;
        User.delete({}, function(response) {
            // delete successful
            // $scope.user = null;
        });
    }

    $scope.register = function() {
        var data = {
            email: $scope.input.email,
            username: $scope.input.username,
            password: $scope.input.password,
            confirm: $scope.input.confirm
        }

        User.save(data, function(response) {
            // post success
            // TODO: show registration errors
        }, function(response) {
            // post failed
        });
    }

};

function MatchListCtrl($scope, $routeParams, Match){
    
    var data = {
        filter : $routeParams.filter
    }
    $scope.matches = Match.query(data);
    
    
    // test data
    $scope.matches = [
        {id: 123,
        agents: ['aoe','qjk'],
        complete: false,
        logs : 'random text'
        },
        {id: 234,
        agents: ['aoe', 'tns'],
        complete: true,
        winner: 'tns',
        logs : 'weee'
        }
    ];
    if($routeParams.filter == 'current') {
        $scope.matches = [
            {id: 123,
            agents: ['aoe', 'qjk'],
            complete: false,
            logs : 'random text'
            }
        ];
    }

};

function MatchCtrl($scope, $routeParams, Match) {

    // FIXME: What if $routeParams.matchId is empty?
    $scope.match = Match.get({matchId: $routeParams.matchId});

    // test data
    $scope.match = {
        id: 123,
        agents: ['aoe','qjk'],
        complete: false, 
        logs : 'random text'
    }

    var cxn = new WebSocket('ws://game.gtagency.org/logs/'+$scope.match.id, ['soap']);
    
    connection.onopen = function() {
        // do nothing
    }

    connection.onerror = function(error) {
        // do nothing
    }

    // recieve logs from the server
    cxn.onmessage = function(e) {
        $scope.logs.append(e.data);
    }

};

function AgentListCtrl($scope, $routeParams) {
    // test data - this controller is not complete
    $scope.agents = [];
    if($routeParams.filter == 'all') {
        $scope.agents = [
            {
                id: 'aoe',
                rank: 1,
                name: 'Botty',
                owner: 'test_user',
                wins: 3,
                losses: 3,
                ties: 0,
                matches: [
                    {
                        id: 123,
                        agents: ['aoe', 'qjk'],
                        complete: false,
                        logs : 'random text'
                    },
                    {
                        id: 234,
                        agents: ['aoe', 'tns'],
                        complete: true,
                        winner: 'aoe',
                        logs : 'weee'
                    }
                ]
            }
        ];
    }
};

function AgentCtrl($scope, $routeParams, Agent) {

    // FIXME: What if $routeParams.agentId is empty?
    $scope.agent = Agent.get({agentId: $routeParams.agentId});

    // test data
    $scope.agent = {
        id: 'aoe',
        rank: 1,
        name: 'Botty',
        owner: 'test_user',
        wins: 3,
        losses: 3,
        ties: 0,
        matches: [
            {
                id: 123,
                agents: ['aoe', 'qjk'],
                complete: false,
            },
            {
                id: 234,
                agents: ['aoe', 'tns'],
                complete: true,
                winner: 'aoe'
            }
        ]
    };

};
