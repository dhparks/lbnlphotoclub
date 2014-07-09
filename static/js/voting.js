frontEnd = {
    totalSelected: 0,
    maxVotes:      3,
    enabled:    true,}
    
// modify the header to display the correct number of votes
var t = $('#t2').text().replace('$maxvotes',frontEnd.maxVotes)
$('#t2').text(t)

// attach click action to the divs which toggles the state
$(".pin").click(function () {
    
    var t = parseInt($(this).attr("vote"));
    
    if (t === 0 && frontEnd.totalSelected < frontEnd.maxVotes && frontEnd.enabled) {
	$(this).attr("vote", 1);
	$(this).css("background","#004499");
	frontEnd.totalSelected += 1;
    }
    
    if (t === 1 && frontEnd.enabled) {
	$(this).attr("vote", 0);
	$(this).css("background-color","#FEFEFE");
	frontEnd.totalSelected += -1;
    }	
})

// stop a click on a link from selecting the photos
$(".link").click(function (event) {event.stopPropagation(); return False;})

// attach the voting action to the submit button
$("#sendvotes").click(function () {

    var onSuccess = function (data) {
	console.log(data);
	frontEnd.enabled = false;
	$(".pin").each(function () {$(this).css("background-color","#FEFEFE")});
	$("#header-wrap").text("Thanks for voting!")
	}

    var submit = function () {

	$("#sendvotes").remove();
	
	$.ajax({
	    url: "castvotes",
	    type: 'POST',
	    data: JSON.stringify({user:'None',photos:selectedPhotos}),
	    contentType: 'application/json; charset=utf-8',
	    dataType: 'json',
	    async: true,
	    success: function (data) {onSuccess(data);}
	    });
	}


    // build the list with a selector
    var selectedPhotos = [];
    $(".pin[vote='1'] img").each(function () {selectedPhotos.push($(this).attr("src"))})
    
    // send information to the backend; wait for response before doing anything in front
    if (frontEnd.enabled) {submit()};

})