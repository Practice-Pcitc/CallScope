package com.example.api;

import com.example.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    /** Return one user. */
    @GetMapping("/{id}")
    public UserDto getUser(@PathVariable Long id) {
        return userService.findUser(id);
    }

    @PostMapping
    public UserDto createUser(@RequestBody UserDto user) {
        return userService.createUser(user);
    }
}
