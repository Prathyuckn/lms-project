toastr.options = {
  closeButton: true,
  debug: false,
  newestOnTop: true,
  progressBar: true,
  positionClass: "toast-bottom-full-width",
  preventDuplicates: true,
  onclick: null,
  showDuration: "300",
  hideDuration: "1000",
  timeOut: "0",
  extendedTimeOut: "0",
  showEasing: "swing",
  hideEasing: "linear",
  showMethod: "fadeIn",
  hideMethod: "fadeOut",
};

// Function to display different types of notifications
function showToastr(type, message, title = "") {
  switch (type) {
    case "success":
      toastr.success(message, title);
      break;
    case "error":
      toastr.error(message, title);
      break;
    case "warning":
      toastr.warning(message, title);
      break;
    case "info":
      toastr.info(message, title);
      break;
    default:
      console.error("Unknown toastr type: " + type);
  }
}
