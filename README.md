mybot
=====


Trying to build myself a personal assistant in python that will keep an eye on my information online.

This is also a learning project where I'm trying to bring together some skills I found important. This means I will make some weird decisions not actually important in a project of this (small) size but will help me simulate and learn how it could be done in a larger and critical project. 

Ex: One of my goals is to make this bot monitor itself, alert me of failures and recover from those failures on its own while I go by my own business and write and deploy code whenever I have 5 minutes available.


# Roadmap

[x] Build a controller module responsible for launching and monitoring BotModules
[x] Write test BotModules running in separate processes and communicating with controller
[x] ConsoleModule for receiving command line commands from and interacting asynchronous console
[x] Asynchronous console with command prompt independent from text output AsyncConsole
[ ] Command interpreter accepting commands for multiple sources and distributing them to the correct BotModule
[ ] EmailModule for communicating with user via email
[ ] Run on a RaspberryPi
[ ] Run second controller responsible for monitoring first controller and relaunch it if needed
[ ] Modules: collecting information from user from various social networks and other internet services
[ ] Twitter communication
[ ] prowl communication 
[ ] Alerts based on collected information: tasks, reminders,...
[ ] How to store that information? 
[ ] Module: awareness of user presence at home
[ ] Module: backup management ?
...
