frontEnd = {
    totalSelected: 0,
    maxVotes:   1000,
    enabled:    true,}

console.log("tiebreaking")

// attach click action to the divs which toggles the state
$(".pin").click(function () {
    
    var t = parseInt($(this).attr("vote"));
    
    console.log(t)
    
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
	$(location).attr('href','/backup')
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
