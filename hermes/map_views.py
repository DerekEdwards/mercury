from extra_utils.extra_shortcuts import render_response

def show_index(request):
    """
    Show index for map page
    This will later be used to display results on a map.  For now it simply displays the index page with status updates
    """
    return render_response(request, 'index.html', {})

