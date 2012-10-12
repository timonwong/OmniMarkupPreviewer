$(function() {
    var query_update = function() {
        var default_interval = 500;
        var buffer_id = $('article').data('buffer-id');
        var timestamp = $('article').data('timestamp');
        var request = {'buffer_id': buffer_id, 'timestamp': timestamp};
        $.ajax({
            type: 'POST',
            url: '/api/query',
            data: JSON.stringify(request),
            dataType: 'json',
            contentType:"application/json; charset=utf-8",
            success: function(entry) {
                //console.log('Old timestamp: %f, New timestamp: %f', timestamp, entry.timestamp);
                if (entry && entry.html_part) {
                    //console.log('Replacing...');
                    // Change title first
                    document.title = entry.filename + '&mdash;' + entry.dirname;
                    $('article').data('timestamp', entry.timestamp);
                    // Replace content with latest one
                    $('article').html(entry.html_part);
                }
            }
        });
    };

    var intervalId = setInterval(query_update, default_interval);

    $(window).focus(function() {
        console.log('Focus');
        if (!intervalId) {
            intervalId = setInterval(query_update, default_interval);
        }
    });

    $(window).blur(function() {
        console.log('Blur');
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
    });
});
