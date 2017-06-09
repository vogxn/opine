var endpoints = {
  getComments: 'http://localhost:8000/comment'
};

function loadComments() {
  var commentList = $('.comments');
  commentList.empty();

  $.getJSON(endpoints.getComments, { title: document.title })
    .done(
    function (data) {
      commentList.append(data.map(jsonToComment))
    });
}

function setupCommentForm() {
  var form = $('#comment-form');
  var submitButton = $('#comment-submit');

  form.on('submit', function (event) {
    event.preventDefault();

    var commentBody = $('#comment-body').val();

    submitButton.prop('disabled', true).text('Submitting...');

    $.ajax({
      url: form.attr('action'), 
      type: form.attr('method'),
      contentType: 'application/json; charset=utf8',
      dataType: 'json',
      data: JSON.stringify({"title": document.title, body:commentBody})
    }).done(function () {
      loadComments();
      $('#comment-body').val('');
    }).always(function () {
      submitButton.prop('disabled', false).text('Submit');
    });
  });
}

// Converts a comment json object into html
function jsonToComment(commentObj) {
  var html = '<li class="comment">' + commentObj.body + '<span class="author">' + commentObj.user.login + '</span></li>'
  return html;
}

$(document).ready(function() {
  loadComments()
  setupCommentForm()
});
