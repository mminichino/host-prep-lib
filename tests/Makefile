.PHONY: images clean ubuntu debian sles amazon redhat rocky oel fedora test
export PYTHONPATH := $(shell pwd)/test:$(shell pwd):$(PYTHONPATH)

images: ubuntu debian sles amazon redhat rocky oel fedora
redhat:
		@if docker image inspect rhel-8-init > /dev/null 2>&1; then docker rmi rhel-8-init; fi
		@if docker image inspect rhel-9-init > /dev/null 2>&1; then docker rmi rhel-9-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t rhel-8-init -f Dockerfile.redhat_8 .
		docker buildx build --load --platform linux/amd64 -t rhel-9-init -f Dockerfile.redhat_9 .
rocky:
		@if docker image inspect rocky-8-init > /dev/null 2>&1; then docker rmi rocky-8-init; fi
		@if docker image inspect rocky-9-init > /dev/null 2>&1; then docker rmi rocky-9-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t rocky-8-init -f Dockerfile.rocky_8 .
		docker buildx build --load --platform linux/amd64 -t rocky-9-init -f Dockerfile.rocky_9 .
oel:
		@if docker image inspect oel-8-init > /dev/null 2>&1; then docker rmi oel-8-init; fi
		@if docker image inspect oel-9-init > /dev/null 2>&1; then docker rmi oel-9-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t oel-8-init -f Dockerfile.oel_8 .
		docker buildx build --load --platform linux/amd64 -t oel-9-init -f Dockerfile.oel_9 .
fedora:
		@if docker image inspect fedora-init > /dev/null 2>&1; then docker rmi fedora-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t fedora-init -f Dockerfile.fedora .
ubuntu:
		@if docker image inspect ubuntu-focal-init > /dev/null 2>&1; then docker rmi ubuntu-focal-init; fi
		@if docker image inspect ubuntu-jammy-init > /dev/null 2>&1; then docker rmi ubuntu-jammy-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t ubuntu-focal-init -f Dockerfile.ubuntu_focal .
		docker buildx build --load --platform linux/arm64 -t ubuntu-focal-init -f Dockerfile.ubuntu_focal .
		docker buildx build --load --platform linux/amd64 -t ubuntu-jammy-init -f Dockerfile.ubuntu_jammy .
		docker buildx build --load --platform linux/arm64 -t ubuntu-jammy-init -f Dockerfile.ubuntu_jammy .
debian:
		@if docker image inspect debian-bullseye-init > /dev/null 2>&1; then docker rmi debian-bullseye-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t debian-bullseye-init -f Dockerfile.debian_bullseye .
sles:
		@if docker image inspect opensuse-init > /dev/null 2>&1; then docker rmi opensuse-init; fi
		@if docker image inspect sles-155-init > /dev/null 2>&1; then docker rmi sles-155-init; fi
		@if docker image inspect sles-153-init > /dev/null 2>&1; then docker rmi sles-153-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t opensuse-init -f Dockerfile.opensuse .
		docker buildx build --load --platform linux/amd64 -t sles-155-init -f Dockerfile.sles_15_5 .
		docker buildx build --load --platform linux/amd64 -t sles-153-init -f Dockerfile.sles_15_3 .
amazon:
		@if docker image inspect amazon-2-init > /dev/null 2>&1; then docker rmi amazon-2-init; fi
		@if docker image inspect amazon-2023-init > /dev/null 2>&1; then docker rmi amazon-2023-init; fi
		docker system prune -f
		docker buildx prune -f
		docker buildx build --load --platform linux/amd64 -t amazon-2-init -f Dockerfile.amazon_2 .
		docker buildx build --load --platform linux/amd64 -t amazon-2023-init -f Dockerfile.amazon_2023 .
clean:
		@if docker image inspect rhel-8-init > /dev/null 2>&1; then docker rmi rhel-8-init; fi
		@if docker image inspect rhel-9-init > /dev/null 2>&1; then docker rmi rhel-9-init; fi
		@if docker image inspect rocky-8-init > /dev/null 2>&1; then docker rmi rocky-8-init; fi
		@if docker image inspect rocky-9-init > /dev/null 2>&1; then docker rmi rocky-9-init; fi
		@if docker image inspect oel-8-init > /dev/null 2>&1; then docker rmi oel-8-init; fi
		@if docker image inspect oel-9-init > /dev/null 2>&1; then docker rmi oel-9-init; fi
		@if docker image inspect fedora-init > /dev/null 2>&1; then docker rmi fedora-init; fi
		@if docker image inspect ubuntu-focal-init > /dev/null 2>&1; then docker rmi ubuntu-focal-init; fi
		@if docker image inspect ubuntu-jammy-init > /dev/null 2>&1; then docker rmi ubuntu-jammy-init; fi
		@if docker image inspect debian-bullseye-init > /dev/null 2>&1; then docker rmi debian-bullseye-init; fi
		@if docker image inspect opensuse-init > /dev/null 2>&1; then docker rmi opensuse-init; fi
		@if docker image inspect sles-155-init > /dev/null 2>&1; then docker rmi sles-155-init; fi
		@if docker image inspect sles-153-init > /dev/null 2>&1; then docker rmi sles-153-init; fi
		@if docker image inspect amazon-2-init > /dev/null 2>&1; then docker rmi amazon-2-init; fi
		@if docker image inspect amazon-2023-init > /dev/null 2>&1; then docker rmi amazon-2023-init; fi
		docker system prune -f
		docker buildx prune -f
test:
		python -m pytest test_1.py
