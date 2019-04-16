// User settings

var initialPages = 70;

// Do not modify below this line

var pagecount = 0;
var overset = false;
var template = ''
var title = ''

$( document ).ready(function() {
	template = '<div class="page"><div class="header"></div><div class="content"></div><div class="footer" id="footer"><div class="pagination"><span class="page-number-current"></span> / <span class="page-number-total"></span></div></div></div>'

    hook();

    addPages(initialPages, 0, $('#article'));
});

function hook(){
    if(document.getNamedFlows()[0]){
        // hook the regionfragmentchange event and, when fired, adjust the number of pages and paginate etc.
        document.getNamedFlows()[0].addEventListener('regionfragmentchange', modifyFlow);
    } else {
        setTimeout(hook, 1000);
    }
}
	
function modifyFlow(e) {
	var article  = $('#article'); 
	var pages  = $('.page-region');

	if (document.getNamedFlows()[0].firstEmptyRegionIndex == -1) {

		if (overset == true) {
			pages.find('.page-number-total').text(pagecount);
			return;
		}

		addPages(11, pagecount, $('#article'));

	} else {
		if (overset == false) {
			overset = true;
		}

		removePages(document.getNamedFlows()[0].firstEmptyRegionIndex);

		pages.find('.page-number-total').text(pagecount);
  	}

}

function addPages(number, offset, appendElement) {
	for(var pageCounter=1; pageCounter<number; pageCounter++) {
	    var template_copy = $(template);

	    appendElement.append(template_copy);

	    template_copy.addClass('page-' + (offset + pageCounter)).find('.page-number-current').text(offset + pageCounter).end();
	    template_copy.addClass('page-region');
  	}

  	pagecount = pagecount + number - 1;
}

function removePages(minimum){
	while (pagecount > minimum) {
		$('.page-' + pagecount).remove();
		pagecount = pagecount - 1;
	}
}
