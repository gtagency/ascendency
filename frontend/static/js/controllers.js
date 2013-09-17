function HomeCtrl($scope) {
    console.log('test');
}

function MatchCtrl($scope, $routeParams) {
    $scope.matchId = $routeParams.matchId;
    
    $scope.match = Match.get({matchId: $scope.matchId}, function(match) {
        // do nothing
    });
}
