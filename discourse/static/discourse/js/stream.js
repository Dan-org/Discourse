$(document).on('click', '.discourse .more', function(e) {
    e.preventDefault();
    var more = $(this);

    if (more.data('loading'))
        return;

    more.data('loading', true);

    $.ajax({
        url: more.attr('href'),
        success: function(response) {
            var size = response.size;
            var results = response.results;
            var next = response.next;

            for(var i = 0; i < results.length; i++) {
                more.before(results[i]);
            }

            more.attr('loading', null);

            if (next) {
                more.attr('href', next);
            } else {
                more.hide();
            }
        }
    });
});