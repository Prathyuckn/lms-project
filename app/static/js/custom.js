$(document).ready(function () {
  //student edit uploaded document modal
  var modal = document.getElementById("editUploadedDocumentModal");
  if (modal != null) {
    modal.addEventListener("show.bs.modal", function (event) {
      // Button that triggered the modal
      var button = event.relatedTarget;
      // Extract info from data-bs-* attributes
      var reportId = button.getAttribute("data-report-id");

      // Update the modal's content.
      var reportIdInput = modal.querySelector(".modal-body #report_id");
      reportIdInput.value = reportId;
    });
  }

  //faculty query response modal
  var queryRespModal = document.getElementById("queryRespModal");
  if (queryRespModal != null) {
    queryRespModal.addEventListener("show.bs.modal", function (event) {
      // Button that triggered the modal
      var button = event.relatedTarget;
      // Extract info from data-bs-* attributes
      var query_id = button.getAttribute("data-bs-query-id");
      // Update the modal's content.
      var queryIdInput = queryRespModal.querySelector(".modal-body #query_id");
      queryIdInput.value = query_id;
    });
  }

  //faculty marks modal
  var marksModal = document.getElementById("marksModal");
  if (marksModal != null) {
    marksModal.addEventListener("show.bs.modal", function (event) {
      // Button that triggered the modal
      var button = event.relatedTarget;

      // Extract info from data-bs-* attributes
      var task_id = button.getAttribute("data-bs-task-id");
      var project_id = button.getAttribute("data-bs-project-id");
      var allotedMarks = button.getAttribute("data-bs-alloted-marks");

      // Update the modal's content.
      var taskIdInput = marksModal.querySelector(".modal-body #task_id");
      var projectIdInput = marksModal.querySelector(".modal-body #project_id");
      var obtainedMarksInput = marksModal.querySelector(
        ".modal-body #obtainedMarks"
      );

      taskIdInput.value = task_id;
      projectIdInput.value = project_id;
      obtainedMarksInput.setAttribute("max", allotedMarks);
    });
  }

  //faculty correction modal
  var reviewModal = document.getElementById("reviewModal");
  if (reviewModal != null) {
    reviewModal.addEventListener("show.bs.modal", function (event) {
      // Button that triggered the modal
      var button = event.relatedTarget;
      // Extract info from data-bs-* attributes
      var report_id = button.getAttribute("data-bs-report-id");
      // Update the modal's content.
      var reportIdInput = reviewModal.querySelector(".modal-body #report_id");
      reportIdInput.value = report_id;
    });
  }

  //student upload document model
  var uploadModal = document.getElementById("uploadModal");
  if (uploadModal != null) {
    uploadModal.addEventListener("show.bs.modal", function (event) {
      // Button that triggered the modal
      var button = event.relatedTarget;
      // Extract info from data-bs-* attributes
      var task_id = button.getAttribute("data-bs-task-id");
      var project_id = button.getAttribute("data-bs-project-id");

      // Update the modal's content.
      var taskIdInput = uploadModal.querySelector(".modal-body #task_id");
      var projectIdInput = uploadModal.querySelector(".modal-body #project_id");
      taskIdInput.value = task_id;
      projectIdInput.value = project_id;
    });
  }

  $("#batchesForm").on("change", "#department_id", function () {
    var deptId = this.value;

    //Get faculties by dept_id
    $.ajax({
      url: "/get-faculties-by-deptid",
      method: "GET",
      data: { deptId: deptId },
      success: function (result) {
        $("#faculty_id").html(result);
      },
    });

    //Get students by dept_id
    $.ajax({
      url: "/get-students-by-deptid",
      method: "GET",
      data: { deptId: deptId },
      success: function (result) {
        $("#stud_id").html(result);
      },
    });
  });
});
