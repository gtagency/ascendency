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

function MatchListCtrl($scope, $routeParams){
    
    // test data - this controller is not complete
    
    $scope.matches = [
        {id: 123,
        'agents': ['aoe','qjk'],
        'complete': false
        },
        {id: 321,
        'agents': ['stth', 'cgr'],
        'complete': true
        }
    ];
    if($routeParams.filter == 'current') {
        $scope.matches = [
            {id: 123,
            'agents': ['aoe', 'qjk'],
            'complete': false
            }
        ];
    }

};

function MatchCtrl($scope) {
};

function AgentListCtrl($scope, $routeParams) {
    // test data - this controller is not complete
    $scope.agents = [];
    if($routeParams.filter == 'all') {
        $scope.agents = [
            {id: 231,
            rank: 1,
            name: 'winner',
            owner: 'test_user',
            wins: 3,
            losses: 3,
            ties: 0}
        ];
    }
};

function AgentCtrl($scope) {

};
