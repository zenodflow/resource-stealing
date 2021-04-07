Resource Stealing
==

After a pod is scheduled to a node, among many other routines going on, the container runtime downloads an image(s), decompress it, and set up the local filesystem. This takes time. Until the image gets *pulled*, the amount of CPU shares assigned to the pod won't be available to the pod.

The idea of cgroups resource stealing is simple: let's temporarily steal the cpu shares from the pod and reassign them to the container runtime so that it *can* leverage more cores when it couldn't do so otherwise.

![steal](doc/steal-explain.png?raw=true)

If multiple containers are pending, the stealing can happen in batch.

![serial-batch-steal](doc/serial-batch-steal.png?raw=true)

After the images are pulled, the cpu shares should be returned to the pods in the amount they were stolen. An integration of resource stealing with kubelet can be found [here](https://github.com/silveryfu/kubelet).


Thanks [Ed](https://github.com/edoakes) for the fun afternoon discussion about this in Soda. Beautiful time. Good, harmless coconut water. Tennis after. Who, unlike me, actually knows about container and actually knows about tennis. Though I always get beaten, even when there is a table for the tennis, I often miss the days.

---

More on speeding up container startup: *Fast and Efficient Container Startup at the Edge via Dependency Scheduling, Silvery Fu, Radhika Mittal, Lei Zhang, Sylvia Ratnasamy, USENIX HotEdge 2020* [[PDF]](https://www.usenix.org/conference/hotedge20/presentation/fu) [[Full version]](http://depsched.s3.amazonaws.com/report.pdf)

