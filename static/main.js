// ===== GLOBAL CONFIG =====
const API = "/api";

// ===== TOKEN =====
function getToken(){
    return localStorage.getItem("token");
}

// ===== AJAX HELPER =====
function api(url, method="GET", data=null){
    return $.ajax({
        url: API + url,
        method: method,
        headers: {
            Authorization: "Bearer " + getToken()
        },
        contentType: "application/json",
        data: data ? JSON.stringify(data) : null
    });
}

// ===== TOAST =====
function toast(msg, ok=true){
    let el = $("#toast");
    el.text(msg)
      .removeClass("bg-red-500 bg-green-500")
      .addClass(ok ? "bg-green-500":"bg-red-500")
      .fadeIn();

    setTimeout(()=> el.fadeOut(), 2500);
}

// ===== AUTH CHECK =====
function checkAuth(){
    if(!getToken()){
        window.location = "/";
    }
}

// ===== LOGOUT =====
function logout(){
    localStorage.removeItem("token");
    window.location = "/";
}