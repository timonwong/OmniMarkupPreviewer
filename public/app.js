$(function() {
    // From http://www.softcomplex.com/docs/get_window_size_and_scrollbar_position.html
    var f_clientWidth = function() {
        return f_filterResults (
            window.innerWidth ? window.innerWidth : 0,
            document.documentElement ? document.documentElement.clientWidth : 0,
            document.body ? document.body.clientWidth : 0
        );
    };

    var f_clientHeight = function() {
        return f_filterResults (
            window.innerHeight ? window.innerHeight : 0,
            document.documentElement ? document.documentElement.clientHeight : 0,
            document.body ? document.body.clientHeight : 0
        );
    };

    var f_scrollLeft = function() {
        return f_filterResults (
            window.pageXOffset ? window.pageXOffset : 0,
            document.documentElement ? document.documentElement.scrollLeft : 0,
            document.body ? document.body.scrollLeft : 0
        );
    };

    var f_scrollTop = function() {
        return f_filterResults (
            window.pageYOffset ? window.pageYOffset : 0,
            document.documentElement ? document.documentElement.scrollTop : 0,
            document.body ? document.body.scrollTop : 0
        );
    };

    var f_filterResults = function(n_win, n_docel, n_body) {
        var n_result = n_win ? n_win : 0;
        if (n_docel && (!n_result || (n_result > n_docel))) {
            n_result = n_docel;
        }
        return n_body && (!n_result || (n_result > n_body)) ? n_body : n_result;
    };

    var get_vertical_scrollbar_props = function() {
        var height = $('html, body').height();
        return {'height': height, 'slider_height': f_clientHeight(), 'slider_pos': f_scrollTop()};
    };

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
                if (entry && (entry.html_part !== null)) {
                    var old_scroll_props = get_vertical_scrollbar_props();
                    // Change title first
                    document.title = entry.filename + '—' + entry.dirname;
                    $('article').data('timestamp', entry.timestamp);
                    // Replace content with latest one
                    $('article').html(entry.html_part);
                    // 'auto' scroll, if necessary
                    var new_scroll_props = get_vertical_scrollbar_props();
                    var increment = new_scroll_props.height - old_scroll_props.height;
                    $('html, body').animate(
                        { scrollTop: old_scroll_props.slider_pos + increment},
                        'fast'
                    );
                }
            }
        });
    };

    var default_interval = 500;
    setInterval(query_update, default_interval);
});