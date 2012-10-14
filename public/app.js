$(function() {
    var default_interval = 500;
    var query_update = function() {
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
                if (entry && entry.html_part) {
                    // Change title first
                    document.title = entry.filename + '—' + entry.dirname;
                    $('article').data('timestamp', entry.timestamp);
                    // Replace content with latest one
                    $('article').html(entry.html_part);
                }
            }
        });
    };

    setInterval(query_update, default_interval);
});
