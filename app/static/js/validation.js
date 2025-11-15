$(document).ready(function () {
  //Custom method for date comparison
  jQuery.validator.addMethod(
    "greaterThan",
    function (value, element, params) {
      if (!/Invalid|NaN/.test(new Date(value))) {
        return new Date(value) > new Date($(params).val());
      }

      return (
        (isNaN(value) && isNaN($(params).val())) ||
        Number(value) > Number($(params).val())
      );
    },
    "Must be greater than {0}."
  );

  // Custom methods only for letters
  jQuery.validator.addMethod(
    "lettersonly",
    function (value, element) {
      return this.optional(element) || /^[a-z\s]+$/i.test(value);
    },
    "Only alphabetical characters"
  );

  $("#changePasswordForm").validate({
    rules: {
      password: {
        minlength: 3,
      },
      confirm_pwd: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      confirm_pwd: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });

  $("#facultyForm").validate({
    rules: {
      email: {
        email: true,
      },
      password: {
        minlength: 3,
      },
    },
  });

  $("#staffForm").validate({
    rules: {
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });

  $("#memberRegistrationForm").validate({
    rules: {
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });

  $("#memberUpdatePassword").validate({
    rules: {
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });
});
