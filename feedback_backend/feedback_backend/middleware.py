# middleware.py
class StaffRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == 'login/' and request.user.is_authenticated:
            if request.user.is_staff:
                return redirect('admin/')
        return self.get_response(request)