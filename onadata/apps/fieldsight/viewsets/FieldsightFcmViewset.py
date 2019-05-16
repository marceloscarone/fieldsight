from rest_framework import viewsets, status, response
from fcm.utils import get_device_model
from fcm.serializers import DeviceSerializer
from rest_framework.authentication import BasicAuthentication
from django.contrib.auth.models import User

from onadata.apps.api.viewsets.xform_viewset import CsrfExemptSessionAuthentication

Device = get_device_model()


class FcmDeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = ()
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def create(self, request, *args, **kwargs):
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        try:
            device = Device.objects.get(dev_id=serializer.data["dev_id"])

        except Device.DoesNotExist:
            device = Device(dev_id=serializer.data["dev_id"])
            device.is_active = True

        device.reg_id = serializer.data["reg_id"]
        user = User.objects.filter(email__iexact=serializer.data["name"])
        if user:
            device.name = user[0].email
        else:
            user = User.objects.filter(username__iexact=serializer.data["name"])
            if user:
                device.name = user[0].email
            else:
                return response.Response(status=status.HTTP_404_NOT_FOUND)
        print(device.__dict__)
        device.save()

    def destroy(self, request, *args, **kwargs):
        try:
            instance = Device.objects.get(dev_id=kwargs["pk"])
            self.perform_destroy(instance)
            return response.Response(status=status.HTTP_200_OK)
        except Device.DoesNotExist:
            return response.Response(status=status.HTTP_404_NOT_FOUND)

    def inactivate(self, request, *args, **kwargs):
        try:
            instance = Device.objects.get(dev_id = request.data.get("dev_id"))
            self.perform_destroy(instance)
            return response.Response(status=status.HTTP_200_OK)
        except Device.DoesNotExist:
            # return response.Response(status=status.HTTP_404_NOT_FOUND)
            return response.Response(status=status.HTTP_200_OK)


    def perform_destroy(self, instance):
        # instance.is_active = False
        instance.delete()
        # instance.save()
