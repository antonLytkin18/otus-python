$(function () {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function vote($this, value) {
        $.ajax($this.attr('href'), {
            'method': 'post',
            'data': {
                'csrfmiddlewaretoken': getCookie('csrftoken'),
                'value': value
            },
            'dataType': 'json',
            'success': function (response) {
                $this.closest('div').find('.rating').text(response.rating);
            }
        });
    }

    function init_vote($container) {
        $container
            .on('click', '.like', function (e) {
                e.preventDefault();
                vote($(this), 1);
            })
            .on('click', '.dislike', function (e) {
                e.preventDefault();
                vote($(this), -1)
            });
    }


    var $answers = $('.answers-list');
    $answers
        .on('click', '.mark-as-solution', function (e) {
            e.preventDefault();
            var $answer = $(this);
            $.ajax($answer.attr('href'), {
                'method': 'post',
                'data': {
                    'csrfmiddlewaretoken': getCookie('csrftoken'),
                },
                'dataType': 'json',
                'success': function (response) {
                    $answer.closest('div').find('.solution-star').toggleClass('far fas');
                    location.reload();
                }
            })
        });

    init_vote($answers);
    init_vote($('.question-vote'));
});

$(function () {
    $('[name=tags]').tagsInput({
        'autocomplete_url': '/tags',
        'height': '45px',
        'width': '400px',
        'onAddTag': function (tag) {
            var $select = $(this),
                tags = $select.val().split(',');
            if (tags.length > 3) {
                tags.shift();
                $select.importTags(tags.join(','));
            }
        }
    })
});