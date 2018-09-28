
$(function() {

    $('.save-expand').on('click', function(e) {
        e.preventDefault();
        $('.save-widget').toggleClass('visible');
    });

    $('.load-expand').on('click', function(e) {
        e.preventDefault();
        $('.script-list').toggleClass('visible');
    });

    $('.delete-link').on('click', function(e) {
        if(!confirm('are you sure you want to delete script "' + $(this).data('name') + '"?')) {
            e.preventDefault();
        }
    });
});
