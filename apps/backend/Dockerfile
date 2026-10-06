# The course's backend image, built inside Minikube (lesson 03):
#   minikube image build -t learning-app/backend:1.0.0 --build-opt=build-arg=APP_VERSION=1.0.0 apps/backend
FROM golang:1.26-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/backend .

FROM gcr.io/distroless/static-debian12:nonroot
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
COPY --from=build /out/backend /backend
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/backend"]
