from . models import CentralSite,Route,TransportClasses
from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render, render_to_response
from bokeh.plotting import figure, output_file, show
from bokeh.models import Legend
from bokeh.embed import components
from django.views.decorators.csrf import ensure_csrf_cookie
import googlemaps
from django.contrib.auth.models import User
import csv
from django.utils import timezone
from django.contrib import auth
import django.contrib.auth.views as auth_views
from bokeh.palettes import Set1
import pandas as pd
from django.core.files.storage import FileSystemStorage
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from .forms import UserRegistrationForm
import django_excel as excel

mykey = open("map_app/static/config.js", "r").readlines()[1]
mykey = mykey.split('\'')


class UploadFileForm(forms.Form):
    file = forms.FileField()


def delete_data(request):
    CentralSite.objects.all().delete()
    Route.objects.all().delete()
    TransportClasses.objects.all().delete()

def login_view(request):
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    user = auth.authenticate(username=username, password=password)
    if user is not None and user.is_active:
        # Correct password, and the user is marked "active"
        auth_views.login(request, user)
        # Redirect to a success page.
        return render(request, 'map_app/login.html')
    else:
        # Show an error page
        return render(request, 'map_app/login_error.html')


def logout_view(request):
    auth_views.logout(request)
    # Redirect to a success page.
    return render(request, 'map_app/logout.html')


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            userObj = form.cleaned_data
            username = userObj['username']
            email =  userObj['email']
            password =  userObj['password']
            if not (User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists()):
                User.objects.create_user(username, email, password)
                user = auth.authenticate(username = username, password = password)
                auth_views.login(request, user)
                return HttpResponseRedirect('/')
            else:
                raise forms.ValidationError('Looks like a username with that email or password already exists')
    else:
        form = UserRegistrationForm()
    return render(request, 'map_app/register.html', {'form' : form})


@ensure_csrf_cookie
def centralLocation(request):

    potentialSites = None; #potentialUploadSucessful = False
    collectionSites = None; #collectionUploadSucessful = False
    transportClass = None; #transportUploadSucessful = False

    if request.method == 'POST'and request.FILES:
        try:
            potentialSites = request.FILES['potentialSitesFile']
            potentialSites_df = pd.read_excel(potentialSites, encoding='utf8')
        except:
            try:
                collectionSites = request.FILES['collectionFile']
                collectionSites = pd.ExcelFile(collectionSites,
                                                sheet_name="Sheet2",
                                                encoding='utf8')
                collectionSites1 = pd.read_excel(collectionSites, 'Sheet1')
                collectionSites2 = pd.read_excel(collectionSites, 'Sheet2')
                collectionSites_df = pd.concat([collectionSites1, collectionSites2])
            except:
                try:
                    transportClass = request.FILES['transportClassFile']
                    transportClass_df = pd.read_excel(transportClass, encoding='utf8')
                except:
                    pass

    broken_addresses = []
    broken_routes = []

    if potentialSites_df is not None:
        # potentialUploadSucessful = True

        for i in range(len(potentialSites_df)):
            print('potsite',potentialSites_df)
            row = potentialSites_df.iloc[i, :]
            try:
                address = row['Address'] + ' South Africa'
                print(address)
                gmaps = googlemaps.Client(key=mykey[1])
                geocode_result = gmaps.geocode(address)
                try:
                    latlng = geocode_result[0]['geometry']['location']
                except:
                    latlng = geocode_result['geometry']['location']

                if not CentralSite.objects.filter(address=row['Address']).exists():
                    query = CentralSite.objects.create(address=row['Address'],
                                                       pub_date=timezone.now(),
                                                       lat=latlng['lat'],
                                                       lng=latlng['lng'],
                                                       costPerMonth = 0)
                    query.save()
                addresses = [latlng['lat'], latlng['lng']]
            except Exception as e:
                print('Address broken. Error:', e)
                broken_addresses.append(row['Address'])

    if collectionSites_df is not None:
        # collectionUploadSucessful = True

        central = CentralSite.objects.order_by('pub_date')

        for i in range(len(collectionSites_df)):
            row = collectionSites_df.iloc[i, :]
            print(row['Address'])
            try:
                address = row['Address'] + ' South Africa'
                gmaps = googlemaps.Client(key=mykey[1])
                geocode_result = gmaps.geocode(address)
                try:
                    latlng = geocode_result[0]['geometry']['location']
                except:
                    latlng = geocode_result['geometry']['location']

                for c in central:
                    distanceDuration =gmaps.distance_matrix(origins = c.address+', South Africa', destinations = row[0]+', South Africa',
                                                        mode = 'driving')

                    if not Route.objects.filter(site= c, address=row['Address']).exists():
                        query = Route.objects.create(site= c,
                                                     address=row['Address'],
                                                     type=row['Collection vehicle'],
                                                     distance_km=round(distanceDuration['rows'][0]['elements'][0]['distance']['value']/1000.0,2),
                                                     duration_minutes = round(distanceDuration['rows'][0]['elements'][0]['duration']['value']/60.0,2),
                                                     deliveriesPerMonth=row['Collections per month'],
                                                     lat=latlng['lat'],
                                                     lng=latlng['lng'])
                        query.save()
            except Exception as e:
                print(e)
                broken_routes.append(row['Address'])

    if transportClass_df is not None:
        # transportUploadSucessful = True
        for i in range(len(transportClass_df)):
            row = transportClass_df.iloc[i, :]
            try:
                query = TransportClasses.objects.create(transport=row['Collection vehicle'],
                                                        costPerKm=row['Cost per km'])
                query.save()
            except Exception as e:
                print(e)

    context = {}
    try:
        central = CentralSite.objects.order_by('pub_date')
        context['central'] = True
        context['central_length'] = len(central)
    except:
        pass

    try:
        routes = Route.objects.order_by('site')

        context['collections'] = True
        context['collections_length'] = len(list(set([r.address for r in routes])))
    except:
        pass

    try:
        transport = TransportClasses.objects.order_by('costPerKm')
        context['transport'] = True
        context['transport_length'] = len(transport)
    except:
        pass

    if len(broken_addresses) > 0:
        context['broken_addresses'] = broken_addresses
        print('Broken addresses', len(broken_addresses))
    if len(broken_routes) > 0:
        context['broken_routes'] = broken_routes
        print('Broken routes', len(broken_routes))

    print(context)
    return render(request, 'map_app/home.html', context,  RequestContext(request))


@ensure_csrf_cookie
def otherLocations(request):
    central = CentralSite.objects.order_by('pub_date')
    transport = TransportClasses.objects.order_by('costPerKm')
    transport = {t.transport:t.costPerKm for t in transport}
    routes = Route.objects.order_by('site')
    potentialAddresses = [[c.lat,c.lng] for c in central]
    collectionAddresses = [[r.lat, r.lng] for r in routes]
    for r in routes:
        r.routeCost = round(r.distance_km*transport[r.type],2)
        r.routeCostPerMonth = round(r.distance_km * transport[r.type] * r.deliveriesPerMonth, 2)
        r.save()

    for c in central:
        y_temp = []
        for rt in routes:
            if rt.site == c:
                y_temp.append(rt.routeCostPerMonth)
        c.costPerMonth = sum(y_temp)
        c.save()

    sites = [(central[i].address,central[i].costPerMonth) for i in range(len(central))]

    filtered = False
    if request.method == 'POST':
        filtered = True
        selected_routes = routes.filter(site=request.POST.get('filter_sites'))

    print(filtered)
    context = {'central':central,
               'num_routes':len(routes)/len(central),
               'sites': sites,
               'potentialAddresses':potentialAddresses,
               'collectionAddresses': collectionAddresses}
    if filtered:
        context['selected_routes'] = selected_routes

    return render(request, 'map_app/otherLocations.html', context,  RequestContext(request))


def downloadSummary(request):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="summary.csv"'

    writer = csv.writer(response)
    central = CentralSite.objects.order_by('pub_date')

    writer.writerow(['Address', 'Transport Cost Per Month'])
    for c in central:
        writer.writerow([str(c.address),str(c.costPerMonth)])

    return response


def downloadDetail(request):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="detail.csv"'

    writer = csv.writer(response)
    routes = Route.objects.order_by('site')


    writer.writerow(['Potential Site','Collection Site',
                     'Duration(min)','Distance(km)',
                     'Deliveries per month',
                     'Transport type','Route Cost(R)',
                     'Route Cost Per Month(R)'])

    for r in routes:
        writer.writerow([str(r.site),str(r.address),
                         str(r.duration_minutes),str(r.distance_km),
                         str(r.deliveriesPerMonth), str(r.type),
                         str(r.routeCost), str(r.routeCostPerMonth),])

    return response


def downloadOrderedByDistance(request):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sitesByDistance.csv"'

    writer = csv.writer(response)
    routes = Route.objects.order_by('distance_km')
    uniqueRoutes = list(set([r.address for r in routes]))
    order = {}
    for add in uniqueRoutes:
        tempRoutes = routes.filter(address = add)
        order[add] = [r.site.address for r in tempRoutes]

    header_row = ['Collection Point'] + ['Site %d'%x for x in range(len(order))]
    writer.writerow(header_row)

    for o in order.keys():
        content_row = [o] + order[o]
        writer.writerow(content_row)

    return response

# def summary(request):
#     central = CentralSite.objects.order_by('pub_date')
#     routes = Route.objects.order_by('site')
#     print([r.routeCost for r in routes])
#
#     title = 'Costs per km'
#
#     p = plot = figure(title= title ,
#         x_axis_label= 'Site Rent',
#         y_axis_label= 'Total Transport Cost per Month',
#         plot_width = 800,
#         plot_height =400,
#         toolbar_location="above")
#     x = [c.rent for c in central]
#     y = []
#     for c in central:
#         y_temp = []
#         for rt in routes:
#             if rt.site == c:
#                 y_temp.append(rt.routeCostPerMonth)
#         print('ytemp',y_temp)
#         y.append(sum(y_temp))
#     leg = []
#     for i in range(len(x)):
#         m = plot.circle(x[i], y[i], size=20, color = Set1[5][i])
#         leg.append((central[i].address,[m]))
#     legend = Legend(items = leg, location=(0, 100))
#     p.add_layout(legend,'right')
#
#     # Store components
#     script, div = components(plot)
#     print(central,x,y)
#     sites = {central[i].address:{'rent':central[i].rent,
#              'cost':y[i]} for i in range(len(central))}
#
#     context = {'script' : script , 'div' : div, 'sites':sites}
#     return render(request, 'map_app/summary.html', context )#,  RequestContext(request))
#
