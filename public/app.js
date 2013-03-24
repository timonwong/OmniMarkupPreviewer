/* jshint forin:true, noarg:true, noempty:true, eqeqeq:true, undef:true, unused:true, curly:true, browser:true, indent:4, maxerr:50 */
/* jshint devel: true */
/* global $, MathJax */

window.App = {};
window.App.Context = {};
window.App.Options = {};

$(function () {
    // From http://www.softcomplex.com/docs/get_window_size_and_scrollbar_position.html

    function filterResult(win, docel, body) {
        var result = win ? win : 0;
        if (docel && (!result || (result > docel))) {
            result = docel;
        }
        return body && (!result || (result > body)) ? body : result;
    }

    function sliderHeight() {
        return filterResult(
            window.innerHeight ? window.innerHeight : 0,
            document.documentElement ? document.documentElement.clientHeight : 0,
            document.body ? document.body.clientHeight : 0);
    }

    function sliderPos() {
        return filterResult(
            window.pageYOffset ? window.pageYOffset : 0,
            document.documentElement ? document.documentElement.scrollTop : 0,
            document.body ? document.body.scrollTop : 0);
    }

    function getVerticalScrollProperties() {
        var height = $('html, body').height();
        return {
            'height': height,
            'sliderHeight': sliderHeight(),
            'sliderPos': sliderPos()
        };
    }

    // Run the scipts of type=text/x-omnimarkup-config
    (function () {
        var scripts = $('script');
        scripts.each(function () {
            var type = String(this.type).replace(/ /g, '');
            if (type.match(/^text\/x-omnimarkup-config(;.*)?$/) && !type.match(/;executed=true/)) {
                this.type += ';executed=true';
                eval(this.innerHTML);
            }
        });
    })();

    function autoScroll(oldScrollProps) {
        var newScrollProps = getVerticalScrollProperties();
        var increment = newScrollProps.height - oldScrollProps.height;
        $('html, body').animate({
            scrollTop: oldScrollProps.sliderPos + increment
        }, 'fast');
    }

    var pollingInterval = window.App.Options.ajax_polling_interval;
    var mathJaxEnabled = window.App.Options.mathjax_enabled;
    var disconnected = false;

    function reviveBuffer() {
        var request = {
            revivable_key: window.App.Context.revivable_key
        };

        $.ajax({
            type: 'POST',
            url: '/api/revive',
            data: JSON.stringify(request),
            dataType: 'json',
            contentType: 'application/json; charset=utf-8'
        }).done(function (data) {
            if (!data) {
                return;
            }

            if (data.status === 'OK') {
                disconnected = false;
                window.location.replace('/view/' + data.buffer_id.toString());
            }
        }).always(function () {
            if (disconnected) {
                setTimeout(reviveBuffer, Math.max(pollingInterval, 600));
            }
        });
    }

    (function poll() {
        var content$ = $('#content');
        var request = {
            buffer_id: window.App.Context.buffer_id,
            timestamp: window.App.Context.timestamp
        };

        setTimeout(function () {
            $.ajax({
                type: 'POST',
                url: '/api/query',
                data: JSON.stringify(request),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8'
            }).done(function (data) {
                // Status <- Online
                if (!data) {
                    return;
                }

                switch (data.status) {
                case 'UNCHANGED':
                    break;
                case 'DISCONNECTED':
                    disconnected = true;
                    break;
                case 'OK':
                    var oldScrollProps = getVerticalScrollProperties();
                    // Fill the filename
                    document.title = data.filename + '\u2014' + data.dirname;
                    $('#filename').text(data.filename);
                    // Replace content with latest one
                    content$.empty().html(data.html_part);
                    window.App.Context.timestamp = data.timestamp;
                    window.App.Context.revivable_key = data.revivable_key;

                    // dirty hack for auto scrolling if images exist
                    var img$ = $('img');
                    var doAutoScroll;
                    if (img$.length > 0) {
                        doAutoScroll = function () {
                            img$.imagesLoaded(function () {
                                autoScroll(oldScrollProps);
                            });
                        };
                    } else {
                        doAutoScroll = function () {
                            autoScroll(oldScrollProps);
                        };
                    }

                    // typeset for MathJax
                    if (mathJaxEnabled) {
                        MathJax.Hub.Queue(
                            ['resetEquationNumbers', MathJax.InputJax.TeX],
                            ['Typeset', MathJax.Hub, content$[0]],
                            doAutoScroll);
                    } else {
                        doAutoScroll();
                    }
                    break;
                }
            }).fail(function () {
                // Status <- Offline
                // console.log('Offline');
            }).always(function () {
                if (!disconnected) {
                    poll();
                } else {
                    reviveBuffer();
                }
            });
        }, pollingInterval);
    })();
});
