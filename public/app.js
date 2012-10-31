$(function() {
    // From http://www.softcomplex.com/docs/get_window_size_and_scrollbar_position.html
    function f_clientWidth() {
        return f_filterResults (
            window.innerWidth ? window.innerWidth : 0,
            document.documentElement ? document.documentElement.clientWidth : 0,
            document.body ? document.body.clientWidth : 0
        );
    }

    function f_clientHeight() {
        return f_filterResults (
            window.innerHeight ? window.innerHeight : 0,
            document.documentElement ? document.documentElement.clientHeight : 0,
            document.body ? document.body.clientHeight : 0
        );
    }

    function f_scrollLeft() {
        return f_filterResults (
            window.pageXOffset ? window.pageXOffset : 0,
            document.documentElement ? document.documentElement.scrollLeft : 0,
            document.body ? document.body.scrollLeft : 0
        );
    }

    function f_scrollTop() {
        return f_filterResults (
            window.pageYOffset ? window.pageYOffset : 0,
            document.documentElement ? document.documentElement.scrollTop : 0,
            document.body ? document.body.scrollTop : 0
        );
    }

    function f_filterResults(n_win, n_docel, n_body) {
        var n_result = n_win ? n_win : 0;
        if (n_docel && (!n_result || (n_result > n_docel))) {
            n_result = n_docel;
        }
        return n_body && (!n_result || (n_result > n_body)) ? n_body : n_result;
    }

    function get_vertical_scrollbar_props() {
        var height = $('html, body').height();
        return {'height': height, 'slider_height': f_clientHeight(), 'slider_pos': f_scrollTop()};
    }

    var polling_interval = parseInt($('#content').data('polling-interval'), 10);

    (function poll() {
        var content$ = $('#content');
        var buffer_id = content$.data('buffer-id');
        var timestamp = content$.data('timestamp');
        var request = {'buffer_id': buffer_id, 'timestamp': timestamp};

        setTimeout(function() {
            $.ajax({
                type: 'POST',
                url: '/api/query',
                data: JSON.stringify(request),
                dataType: 'json',
                contentType:"application/json; charset=utf-8",
                success: function(data) {
                    if (data && (data.html_part !== null)) {
                        var old_scroll_props = get_vertical_scrollbar_props();
                        // Fill the filename
                        document.title = data.filename + '\u2014' + data.dirname;
                        $('#filename').text(data.filename);
                        content$.data('timestamp', data.timestamp);
                        // Replace content with latest one
                        content$.html(data.html_part);
                        // 'auto' scroll, if necessary
                        var new_scroll_props = get_vertical_scrollbar_props();
                        var increment = new_scroll_props.height - old_scroll_props.height;
                        $('html, body').animate(
                            { scrollTop: old_scroll_props.slider_pos + increment},
                            'fast'
                        );
                    }
                },
                complete: poll
            });
        }, polling_interval);
    })();
});
