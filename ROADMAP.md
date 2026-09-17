# Direction

Use the official TypeSafe skill/docs for knowledge and the official SDK for provider
traffic. Maintain only the execution value added by this project. Avoid competing
skills, mirrored cookbooks and a second SDK.

Next checks: one authorized real Jev response on the user's host, then actual
workflow latency/error measurements. Consider bounded parallelism or richer job
management only from those measurements; current batches remain sequential.

SDK updates require compatibility tests. Host-specific onboarding and real account
access are verified separately from synthetic tests. Do not invent accuracy or
cost superiority over the official components.
