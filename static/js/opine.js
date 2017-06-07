var endpoints = {
  getComments: 'https://gist.githubusercontent.com/vogxn/d8b050d0b2e09786a634d95ae1eab6be/raw/0ef116c8ffae125b9190443382955720e8d9d0f2/opine_comment.json'
};

function loadComments() {
  var commentList = $('.comments');
  commentList.empty();

  $.getJSON(endpoints.getComments, function (data) {
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
      dataType: 'json',
      data: JSON.stringify({ body: commentBody })
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
};
